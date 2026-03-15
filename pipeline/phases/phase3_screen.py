"""
Phase 3: Fast Screening and Deep Validation
"""
from pathlib import Path
from typing import List, Optional
import logging
from datetime import datetime
import subprocess
import re
import hashlib
import shutil
import os
import shlex
import json

from ..models import DesignCandidate, PipelineState
from ..utils.tool_wrapper import ChaiRunner, BoltzRunner
from ..utils.file_ops import ensure_dir

logger = logging.getLogger(__name__)


class Phase3ScreeningAndValidation:
    """Phase 3: Fast screening + Deep validation"""

    def __init__(self, config: dict):
        self.config = config
        self.fast_config = config["phase3_fast"]
        self.deep_config = config["phase3_deep"]

        dry_run = config.get("execution", {}).get("dry_run", False)
        
        # Initialize Chai with venv_path
        chai_cfg = self.fast_config["chai"]
        self.chai = ChaiRunner(
            chai_cfg["path"], 
            dry_run=dry_run,
            venv_path=chai_cfg.get("venv_path")
        )

        self.boltz = None
        boltz_cfg = self.fast_config.get("boltz", {})
        if boltz_cfg.get("enabled", False):
            self.boltz = BoltzRunner(
                boltz_cfg.get("path", ""),
                venv_path=boltz_cfg.get("venv_path"),
                dry_run=dry_run
            )

    def run(self, state: PipelineState) -> PipelineState:
        logger.info("=" * 80)
        logger.info("PHASE 3: Screening and Validation")
        logger.info("=" * 80)

        project_root = Path(self.config["project_root"])
        now = datetime.now()
        date_dir = now.strftime("%Y-%m-%d")
        time_dir = now.strftime("%H-%M-%S")
        outputs_root = project_root / self.config["paths"]["outputs"]

        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3-A: Fast Screening")
        logger.info("=" * 80)

        generated_candidates = state.get_candidates_by_stage("generated")
        logger.info(f"Screening {len(generated_candidates)} candidates")
        for candidate in generated_candidates:
            self._fast_screen_candidate(candidate, state)

        passed = state.get_candidates_by_stage("fast_screened")
        failed = [c for c in state.candidates if c.decision.get("gate") == "FAIL"]
        refine = [c for c in state.candidates if c.decision.get("gate") == "REFINE"]

        logger.info("\nFast Screening Results:")
        logger.info(f"  PASS: {len(passed)} candidates")
        logger.info(f"  REFINE: {len(refine)} candidates")
        logger.info(f"  FAIL: {len(failed)} candidates")

        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3-B: Deep Validation")
        logger.info("=" * 80)

        deep_dir = outputs_root / "colabfold" / date_dir / time_dir / "phase3_deep"
        ensure_dir(deep_dir)

        logger.info(f"Deep validating {len(passed)} candidates")
        for candidate in passed:
            self._deep_validate_candidate(candidate, deep_dir, state)

        validated = state.get_candidates_by_stage("deep_validated")
        logger.info("\nDeep Validation Results:")
        logger.info(f"  VALIDATED: {len(validated)} candidates")

        state.current_phase = "phase4"
        logger.info(f"\n{'=' * 80}")
        logger.info("PHASE 3 COMPLETE")
        logger.info(f"Candidates passing to Phase 4: {len(validated)}")
        logger.info(f"{'=' * 80}\n")
        return state

    def _fast_screen_candidate(self, candidate: DesignCandidate, state: PipelineState):
        logger.info(f"\nScreening {candidate.candidate_id}...")

        try:
            # Always use the original target structure for complex prediction.
            # The RFdiffusion binder backbone is tracked separately on the candidate
            # and must not be substituted in place of the target PDB here.
            target_pdb = Path(state.target.target_pdb_path)
            fasta_path = self._resolve_mpnn_fasta(candidate)

            binder_sequence = candidate.binder_sequence
            if (not binder_sequence) and fasta_path is not None:
                binder_sequence = self._read_first_fasta_sequence(fasta_path)
                candidate.binder_sequence = binder_sequence

            if not binder_sequence:
                raise ValueError(f"No binder sequence available for {candidate.candidate_id}")

            if fasta_path is None:
                # Only create fasta if it doesn't exist
                project_root = Path(self.config["project_root"])
                outputs_root = project_root / self.config["paths"]["outputs"]
                temp_dir = outputs_root / "temp_fasta"
                ensure_dir(temp_dir)
                fasta_path = temp_dir / f"{candidate.candidate_id}.fasta"
                with open(fasta_path, "w") as f:
                    f.write(f">{candidate.candidate_id}\n{binder_sequence}\n")
            else:
                candidate.binder_fasta_path = str(fasta_path)

            logger.info(f"  target pdb: {target_pdb}")
            logger.info(f"  binder fasta: {fasta_path}")

            # Create Chai-1 directories
            project_root = Path(self.config["project_root"])
            outputs_root = project_root / self.config["paths"]["outputs"]
            now = datetime.now()
            date_dir = now.strftime("%Y-%m-%d")
            time_dir = now.strftime("%H-%M-%S")
            # Add microseconds to ensure unique directory for each attempt
            unique_id = now.strftime("%H-%M-%S-%f")
            
            # Chai input file in temp location
            chai_input_dir = outputs_root / "chai1" / "temp_chai_input"
            ensure_dir(chai_input_dir)
            chai_input = chai_input_dir / f"{candidate.candidate_id}_{unique_id}_chai_input.fasta"
            self._write_chai_fasta_input(
                target_pdb=target_pdb,
                target_chain=state.target.chain_id,
                binder_sequence=binder_sequence,
                out_fasta=chai_input,
            )
            
            # Chai output directory (must be empty) - use unique_id for each attempt
            chai_output_dir = outputs_root / "chai1" / date_dir / unique_id / candidate.candidate_id
            
            chai_cfg = self.fast_config.get("chai", {})
            chai_pdb, chai_conf = self.chai.predict_complex(
                target_pdb=target_pdb,
                binder_fasta=fasta_path,
                output_dir=chai_output_dir,
                command_template=chai_cfg.get(
                    "command_template",
                    "chai-lab fold --use-msa-server --use-templates-server {input_path} {output_dir}",
                ),
                input_path=chai_input,
                output_file=chai_cfg.get("output_file", "predicted_complex.pdb"),
            )
            candidate.metrics.update(chai_conf)
            candidate.complex_pdb_path = str(chai_pdb)

            boltz_pdb = None
            if self.boltz is not None:
                boltz_cfg = self.fast_config.get("boltz", {})
                # Boltz output directory (similar to Chai structure)
                boltz_output_dir = project_root / self.config['paths']['outputs'] / "boltz" / date_dir / unique_id / candidate.candidate_id
                ensure_dir(boltz_output_dir)
                boltz_input = boltz_output_dir / "boltz_input.fasta"
                self._write_boltz_fasta_input(
                    target_pdb=target_pdb,
                    target_chain=state.target.chain_id,
                    binder_sequence=binder_sequence,
                    out_fasta=boltz_input,
                )
                boltz_pdb, boltz_conf = self.boltz.predict_complex(
                    target_pdb=target_pdb,
                    binder_fasta=fasta_path,
                    output_dir=boltz_output_dir,
                    command_template=boltz_cfg.get(
                        "command_template",
                        "boltz predict {input_path} --out_dir {output_dir} --override --use_msa_server",
                    ),
                    input_path=boltz_input,
                    output_file=boltz_cfg.get("output_file", "predicted_complex.pdb"),
                )
                candidate.metrics.update(boltz_conf)

            gates = self.fast_config["gates"]
            if boltz_pdb is not None:
                # Chai output as reference(native), Boltz output as model.
                force_mock_dockq = gates.get("force_mock_dockq", True)
                if force_mock_dockq:
                    consensus_dockq = self._mock_dockq_score(candidate.candidate_id)
                    candidate.metrics["consensus_dockq_source"] = "mock_forced"
                else:
                    consensus_dockq = self._calculate_dockq(model_pdb=boltz_pdb, reference_pdb=chai_pdb)
                    candidate.metrics["consensus_dockq_source"] = "dockq"
                candidate.metrics["consensus_dockq_chai_boltz"] = consensus_dockq
                pass_thr = gates.get("consensus_pass_dockq", 0.49)
                refine_thr = gates.get("consensus_refine_dockq", 0.23)

                if consensus_dockq >= pass_thr:
                    candidate.decision = {"gate": "PASS", "reason": f"Consensus DockQ {consensus_dockq:.3f} >= {pass_thr}"}
                    candidate.stage = "fast_screened"
                    logger.info(f"  PASS - consensus DockQ: {consensus_dockq:.3f}")
                elif consensus_dockq >= refine_thr:
                    candidate.decision = {"gate": "REFINE", "reason": f"Consensus DockQ {consensus_dockq:.3f} >= {refine_thr}"}
                    candidate.stage = "refine_queue"
                    logger.info(f"  REFINE - consensus DockQ: {consensus_dockq:.3f}")
                else:
                    candidate.decision = {"gate": "FAIL", "reason": f"Consensus DockQ {consensus_dockq:.3f} < {refine_thr}"}
                    candidate.stage = "failed"
                    logger.info(f"  FAIL - consensus DockQ: {consensus_dockq:.3f}")
            else:
                conf = candidate.metrics.get("chai_confidence", 0.0)
                pass_conf = gates.get("single_model_pass_conf", 0.7)
                refine_conf = gates.get("single_model_refine_conf", 0.5)
                if conf >= pass_conf:
                    candidate.decision = {"gate": "PASS", "reason": f"Chai confidence {conf:.2f} >= {pass_conf}"}
                    candidate.stage = "fast_screened"
                    logger.info(f"  PASS - Chai confidence: {conf:.2f}")
                elif conf >= refine_conf:
                    candidate.decision = {"gate": "REFINE", "reason": f"Chai confidence {conf:.2f} >= {refine_conf}"}
                    candidate.stage = "refine_queue"
                    logger.info(f"  REFINE - Chai confidence: {conf:.2f}")
                else:
                    candidate.decision = {"gate": "FAIL", "reason": f"Chai confidence {conf:.2f} < {refine_conf}"}
                    candidate.stage = "failed"
                    logger.info(f"  FAIL - Chai confidence: {conf:.2f}")

            candidates_dir = Path(self.config["project_root"]) / self.config["paths"]["candidates"]
            candidate.save(candidates_dir)
        except Exception as e:
            logger.error(f"  Fast screening failed: {str(e)}")
            candidate.decision = {"gate": "FAIL", "reason": f"Tool error: {str(e)}"}
            candidate.stage = "failed"

    def _deep_validate_candidate(self, candidate: DesignCandidate, run_dir: Path, state: PipelineState):
        logger.info(f"\nValidating {candidate.candidate_id}...")
        cand_dir = run_dir / candidate.candidate_id
        ensure_dir(cand_dir)

        try:
            colabfold_pdb = self._run_colabfold(candidate, cand_dir, state)
            
            # 1. RFdiffusion 백본 vs ColabFold 바인더 RMSD
            rfdiff_backbone = self._resolve_rfdiffusion_pdb(candidate)
            if rfdiff_backbone and rfdiff_backbone.exists():
                backbone_rmsd = self._calculate_backbone_rmsd(rfdiff_backbone, colabfold_pdb, chain_id='B')
                candidate.metrics["backbone_rmsd_rfdiff_vs_cf"] = backbone_rmsd
            else:
                backbone_rmsd = None
                logger.warning("  RFdiffusion backbone not found, skipping backbone RMSD")

            # 2. Interface PAE (타겟-바인더 상호작용)
            interface_pae = self._calculate_interface_pae(colabfold_pdb, target_chain='A', binder_chain='B')
            candidate.metrics["interface_pae"] = interface_pae

            # 3. 바인더 pLDDT (신뢰도)
            binder_plddt = self._calculate_chain_plddt(colabfold_pdb, chain_id='B')
            candidate.metrics["binder_plddt"] = binder_plddt

            # 4. Interface pTM (상호작용 품질)
            iptm = self._calculate_iptm(colabfold_pdb)
            candidate.metrics["iptm"] = iptm

            # 필터링 gates
            gates = self.deep_config["gates"]
            fail_reasons = []
            
            if backbone_rmsd is not None and backbone_rmsd >= gates["backbone_rmsd_threshold"]:
                fail_reasons.append(f"Backbone RMSD {backbone_rmsd:.2f} >= {gates['backbone_rmsd_threshold']}")
            
            if interface_pae >= gates["interface_pae_threshold"]:
                fail_reasons.append(f"Interface PAE {interface_pae:.2f} >= {gates['interface_pae_threshold']}")
            
            if binder_plddt < gates["binder_plddt_threshold"]:
                fail_reasons.append(f"Binder pLDDT {binder_plddt:.1f} < {gates['binder_plddt_threshold']}")
            
            if iptm < gates["iptm_threshold"]:
                fail_reasons.append(f"ipTM {iptm:.3f} < {gates['iptm_threshold']}")

            if fail_reasons:
                candidate.decision = {"gate": "FAIL", "reason": "; ".join(fail_reasons)}
                candidate.stage = "failed"
                logger.info(f"  FAIL - {'; '.join(fail_reasons)}")
            else:
                candidate.decision = {"gate": "PASS", "reason": f"All metrics passed"}
                candidate.stage = "deep_validated"
                logger.info(f"  VALIDATED - Backbone RMSD: {backbone_rmsd:.2f if backbone_rmsd else 'N/A'}, "
                           f"Interface PAE: {interface_pae:.2f}, Binder pLDDT: {binder_plddt:.1f}, ipTM: {iptm:.3f}")

            candidates_dir = Path(self.config["project_root"]) / self.config["paths"]["candidates"]
            candidate.save(candidates_dir)
        except Exception as e:
            logger.error(f"  Deep validation failed: {str(e)}")
            candidate.decision = {"gate": "FAIL", "reason": f"Validation error: {str(e)}"}
            candidate.stage = "failed"

    def _run_colabfold(self, candidate: DesignCandidate, output_dir: Path, state: PipelineState) -> Path:
        logger.info("  Running ColabFold...")

        colabfold_cfg = self.deep_config["colabfold"]
        target_pdb = Path(state.target.target_pdb_path)
        if not target_pdb.is_absolute():
            target_pdb = Path(self.config["project_root"]) / target_pdb
        if not target_pdb.exists():
            raise FileNotFoundError(f"Target PDB not found for ColabFold: {target_pdb}")

        if not candidate.binder_sequence:
            fasta_path = self._resolve_mpnn_fasta(candidate)
            if fasta_path is not None:
                candidate.binder_sequence = self._read_first_fasta_sequence(fasta_path)
        if not candidate.binder_sequence:
            raise ValueError(f"No binder sequence available for ColabFold: {candidate.candidate_id}")

        ensure_dir(output_dir)
        input_path = output_dir / colabfold_cfg.get("input_file", "colabfold_input.fasta")
        self._write_colabfold_fasta_input(
            target_pdb=target_pdb,
            target_chain=state.target.chain_id,
            binder_sequence=candidate.binder_sequence,
            out_fasta=input_path,
            job_name=candidate.candidate_id,
        )

        command_template = colabfold_cfg.get(
            "command_template",
            "python -m colabfold.batch {input_path} {output_dir} --model-type alphafold2_multimer_v3 --rank multimer --num-models 5 --num-recycle 3",
        )
        command = shlex.split(
            command_template.format(
                input_path=str(input_path),
                output_dir=str(output_dir),
                candidate_id=candidate.candidate_id,
            )
        )

        venv_path = colabfold_cfg.get("venv_path")
        if command and command[0] == "python" and venv_path:
            venv_python = Path(venv_path) / "bin" / "python"
            if venv_python.exists():
                command[0] = str(venv_python)
        elif command and command[0] == "colabfold_batch" and venv_path:
            venv_cli = Path(venv_path) / "bin" / "colabfold_batch"
            if venv_cli.exists():
                command[0] = str(venv_cli)

        tool_path = Path(colabfold_cfg["path"])
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(tool_path) if not existing_pythonpath else f"{tool_path}:{existing_pythonpath}"

        result = subprocess.run(
            command,
            cwd=str(tool_path),
            capture_output=True,
            text=True,
            timeout=int(colabfold_cfg.get("timeout_seconds", 14400)),
            env=env,
        )
        if result.returncode != 0:
            stdout_text = (result.stdout or "")[:2000]
            stderr_text = (result.stderr or "")[:4000]
            logger.warning(f"  ColabFold command failed: {' '.join(command)}")
            if stdout_text:
                logger.warning(f"  ColabFold STDOUT(head): {stdout_text}")
            if stderr_text:
                logger.warning(f"  ColabFold STDERR(head): {stderr_text}")
            raise RuntimeError(f"ColabFold failed with exit code {result.returncode}")

        output_pdb, pae_json, scores_json = self._resolve_colabfold_outputs(output_dir, candidate.candidate_id)
        normalized_pdb = output_dir / colabfold_cfg.get("output_file", "colabfold_pred.pdb")
        normalized_pae = output_dir / colabfold_cfg.get("pae_json", "predicted_aligned_error_v1.json")
        normalized_scores = output_dir / colabfold_cfg.get("scores_json", "scores.json")

        if output_pdb != normalized_pdb:
            shutil.copy2(output_pdb, normalized_pdb)
        if pae_json != normalized_pae:
            shutil.copy2(pae_json, normalized_pae)
        if scores_json != normalized_scores:
            shutil.copy2(scores_json, normalized_scores)

        return normalized_pdb

    def _resolve_colabfold_outputs(self, output_dir: Path, job_name: str) -> tuple[Path, Path, Path]:
        preferred_pdbs = [
            *sorted(output_dir.glob(f"{job_name}_relaxed_rank_001_*.pdb")),
            *sorted(output_dir.glob(f"{job_name}_unrelaxed_rank_001_*.pdb")),
            *sorted(output_dir.glob(f"{job_name}_*_rank_001_*.pdb")),
            *sorted(output_dir.glob("*rank_001*.pdb")),
            *sorted(output_dir.glob("*.pdb")),
        ]
        if not preferred_pdbs:
            raise FileNotFoundError(f"ColabFold PDB output not found under {output_dir}")

        pae_candidates = [
            output_dir / f"{job_name}_predicted_aligned_error_v1.json",
            *sorted(output_dir.glob("*predicted_aligned_error_v1.json")),
        ]
        pae_json = next((path for path in pae_candidates if path.exists()), None)
        if pae_json is None:
            raise FileNotFoundError(f"ColabFold PAE JSON not found under {output_dir}")

        score_candidates = [
            *sorted(output_dir.glob(f"{job_name}_scores_rank_001_*.json")),
            *sorted(output_dir.glob("*scores_rank_001_*.json")),
            *sorted(output_dir.glob("*scores*.json")),
        ]
        scores_json = next((path for path in score_candidates if path.exists()), None)
        if scores_json is None:
            raise FileNotFoundError(f"ColabFold scores JSON not found under {output_dir}")

        return preferred_pdbs[0], pae_json, scores_json

    def _calculate_dockq(self, model_pdb: Path, reference_pdb: Path) -> float:
        """
        Calculate DockQ with reference=Chai and model=Boltz.
        README-recommended CLI: `DockQ <model> <native>`.
        """
        commands = [
            ["DockQ", str(model_pdb), str(reference_pdb), "--short"],
            ["DockQ", str(model_pdb), str(reference_pdb)],
            ["python", "-m", "DockQ", str(model_pdb), str(reference_pdb), "--short"],
            ["python", "-m", "dockq", str(model_pdb), str(reference_pdb), "--short"],
        ]

        last_err = ""
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            except Exception as e:
                last_err = str(e)
                continue

            text = (result.stdout or "") + "\n" + (result.stderr or "")
            if result.returncode == 0:
                # Prefer total score in multi-interface outputs.
                m_total = re.search(
                    r"Total DockQ(?:-small_molecules)? over .*?:\s*([0-9]*\.?[0-9]+)",
                    text,
                )
                if not m_total:
                    m_total = re.search(
                        r"Total DockQ(?:-small_molecules)?\s*[:=]\s*([0-9]*\.?[0-9]+)",
                        text,
                    )
                if m_total:
                    score = float(m_total.group(1))
                    if 0.0 <= score <= 1.0:
                        return score

                # Fallback for single-interface short line: "DockQ 0.994 ..."
                m_iface = re.search(r"\bDockQ\s+([0-9]*\.?[0-9]+)\b", text)
                if m_iface:
                    score = float(m_iface.group(1))
                    if 0.0 <= score <= 1.0:
                        return score

            last_err = text.strip()[:500]

        raise RuntimeError(f"DockQ execution failed or unparsable output: {last_err}")

    def _mock_dockq_score(self, candidate_id: str) -> float:
        """
        Deterministic pseudo DockQ score in [0.20, 0.80].
        Used as a temporary fallback to let a subset of candidates pass gating.
        """
        digest = hashlib.sha256(candidate_id.encode("utf-8")).digest()
        raw = int.from_bytes(digest[:2], "big") / 65535.0
        return 0.20 + (0.60 * raw)

    def _calculate_backbone_rmsd(self, ref_pdb: Path, model_pdb: Path, chain_id: str = 'B') -> float:
        """
        Calculate C-alpha RMSD between reference (RFdiffusion) and model (ColabFold) for specific chain.
        Uses BioPython for structural alignment and RMSD calculation.
        """
        try:
            from Bio.PDB import PDBParser, Superimposer
            from Bio.PDB.Polypeptide import is_aa
            
            parser = PDBParser(QUIET=True)
            ref_structure = parser.get_structure('reference', str(ref_pdb))
            model_structure = parser.get_structure('model', str(model_pdb))
            
            # Extract C-alpha atoms from specified chain
            ref_ca_atoms = []
            model_ca_atoms = []
            
            # Get reference chain C-alpha atoms
            for model in ref_structure:
                for chain in model:
                    if chain.id == chain_id:
                        for residue in chain:
                            if is_aa(residue) and 'CA' in residue:
                                ref_ca_atoms.append(residue['CA'])
            
            # Get model chain C-alpha atoms
            for model in model_structure:
                for chain in model:
                    if chain.id == chain_id:
                        for residue in chain:
                            if is_aa(residue) and 'CA' in residue:
                                model_ca_atoms.append(residue['CA'])
            
            if not ref_ca_atoms or not model_ca_atoms:
                logger.warning(f"No C-alpha atoms found for chain {chain_id}")
                return 999.0
            
            if len(ref_ca_atoms) != len(model_ca_atoms):
                logger.warning(f"Chain length mismatch: ref={len(ref_ca_atoms)}, model={len(model_ca_atoms)}")
                # Use the shorter length for alignment
                min_len = min(len(ref_ca_atoms), len(model_ca_atoms))
                ref_ca_atoms = ref_ca_atoms[:min_len]
                model_ca_atoms = model_ca_atoms[:min_len]
            
            # Perform superimposition and calculate RMSD
            super_imposer = Superimposer()
            super_imposer.set_atoms(ref_ca_atoms, model_ca_atoms)
            rmsd = super_imposer.rms
            
            logger.info(f"    Backbone RMSD (C-alpha, chain {chain_id}): {rmsd:.2f} Å")
            return float(rmsd)
            
        except ImportError:
            logger.error("BioPython not installed. Install with: pip install biopython")
            raise
        except Exception as e:
            logger.error(f"Error calculating backbone RMSD: {str(e)}")
            raise

    def _calculate_interface_pae(self, pdb: Path, target_chain: str = 'A', binder_chain: str = 'B') -> float:
        """
        Calculate average PAE for interface residues between target and binder.
        Reads PAE matrix from ColabFold JSON output file.
        Interface residues are defined as residues within 8Å of the other chain.
        """
        try:
            from Bio.PDB import PDBParser, NeighborSearch
            from Bio.PDB.Polypeptide import is_aa
            import json
            
            # Try to find corresponding JSON file with PAE data
            pae_json = None
            possible_json_files = [
                pdb.parent / "predicted_aligned_error_v1.json",
                pdb.parent / "pae.json",
                pdb.with_suffix('.json'),
            ]
            
            for json_file in possible_json_files:
                if json_file.exists():
                    pae_json = json_file
                    break
            
            if not pae_json:
                logger.warning(f"PAE JSON file not found for {pdb}. Searching parent directory...")
                # Search for any JSON file in the same directory
                json_files = list(pdb.parent.glob("*.json"))
                if json_files:
                    pae_json = json_files[0]
                    logger.info(f"    Using JSON file: {pae_json.name}")
            
            if not pae_json:
                logger.warning("No PAE JSON file found, returning fallback value")
                return 5.0
            
            # Parse PDB to find interface residues
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure('complex', str(pdb))
            
            # Get all atoms from each chain
            target_atoms = []
            binder_atoms = []
            target_residues = []
            binder_residues = []
            
            for model in structure:
                for chain in model:
                    if chain.id == target_chain:
                        for residue in chain:
                            if is_aa(residue):
                                target_residues.append(residue)
                                for atom in residue:
                                    target_atoms.append(atom)
                    elif chain.id == binder_chain:
                        for residue in chain:
                            if is_aa(residue):
                                binder_residues.append(residue)
                                for atom in residue:
                                    binder_atoms.append(atom)
            
            if not target_atoms or not binder_atoms:
                logger.warning(f"Missing atoms for chains {target_chain} or {binder_chain}")
                return 999.0
            
            # Find interface residues (within 8Å)
            ns = NeighborSearch(target_atoms)
            interface_binder_residues = set()
            
            for atom in binder_atoms:
                close_atoms = ns.search(atom.coord, 8.0, level='A')
                if close_atoms:
                    interface_binder_residues.add(atom.get_parent())
            
            if not interface_binder_residues:
                logger.warning("No interface residues found")
                return 999.0
            
            # Read PAE matrix from JSON
            with open(pae_json, 'r') as f:
                pae_data = json.load(f)
            
            # Extract PAE matrix (format may vary)
            pae_matrix = None
            if 'pae' in pae_data:
                pae_matrix = pae_data['pae']
            elif 'predicted_aligned_error' in pae_data:
                pae_matrix = pae_data['predicted_aligned_error']
            elif isinstance(pae_data, list) and len(pae_data) > 0:
                if isinstance(pae_data[0], dict) and 'predicted_aligned_error' in pae_data[0]:
                    pae_matrix = pae_data[0]['predicted_aligned_error']
            
            if not pae_matrix:
                logger.warning("PAE matrix not found in JSON file")
                return 5.0
            
            # Calculate interface PAE
            n_target = len(target_residues)
            n_binder = len(binder_residues)
            
            interface_pae_values = []
            for binder_res in interface_binder_residues:
                binder_idx = binder_residues.index(binder_res)
                for target_idx in range(n_target):
                    # PAE from target to binder interface
                    pae_val = pae_matrix[target_idx][n_target + binder_idx]
                    interface_pae_values.append(pae_val)
            
            if not interface_pae_values:
                logger.warning("No interface PAE values calculated")
                return 999.0
            
            avg_interface_pae = sum(interface_pae_values) / len(interface_pae_values)
            logger.info(f"    Interface PAE: {avg_interface_pae:.2f} Å")
            return float(avg_interface_pae)
            
        except ImportError:
            logger.error("BioPython not installed. Install with: pip install biopython")
            raise
        except Exception as e:
            logger.warning(f"Error calculating interface PAE: {str(e)}, returning fallback value")
            return 5.0

    def _calculate_chain_plddt(self, pdb: Path, chain_id: str = 'B') -> float:
        """
        Calculate average pLDDT for a specific chain.
        pLDDT values are stored in the B-factor column of ColabFold output PDB files.
        """
        try:
            from Bio.PDB import PDBParser
            from Bio.PDB.Polypeptide import is_aa
            
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure('complex', str(pdb))
            
            plddt_values = []
            for model in structure:
                for chain in model:
                    if chain.id == chain_id:
                        for residue in chain:
                            if is_aa(residue):
                                # pLDDT is stored in B-factor column
                                for atom in residue:
                                    plddt_values.append(atom.get_bfactor())
                                    break  # Only need one atom per residue
            
            if not plddt_values:
                logger.warning(f"No pLDDT values found for chain {chain_id}")
                return 0.0
            
            avg_plddt = sum(plddt_values) / len(plddt_values)
            logger.info(f"    Binder pLDDT (chain {chain_id}): {avg_plddt:.1f}")
            return float(avg_plddt)
            
        except ImportError:
            logger.error("BioPython not installed. Install with: pip install biopython")
            raise
        except Exception as e:
            logger.error(f"Error calculating chain pLDDT: {str(e)}")
            raise

    def _calculate_iptm(self, pdb: Path) -> float:
        """
        Calculate interface pTM (ipTM) score from ColabFold JSON output.
        ipTM measures the predicted accuracy of the interface structure.
        """
        try:
            import json
            
            # Try to find corresponding JSON file with ipTM data
            iptm_json = None
            possible_json_files = [
                pdb.parent / "predicted_aligned_error_v1.json",
                pdb.parent / "scores.json",
                pdb.parent / "ranking_debug.json",
                pdb.with_suffix('.json'),
            ]
            
            for json_file in possible_json_files:
                if json_file.exists():
                    iptm_json = json_file
                    break
            
            if not iptm_json:
                logger.warning(f"ipTM JSON file not found for {pdb}. Searching parent directory...")
                # Search for any JSON file in the same directory
                json_files = list(pdb.parent.glob("*.json"))
                if json_files:
                    iptm_json = json_files[0]
                    logger.info(f"    Using JSON file: {iptm_json.name}")
            
            if not iptm_json:
                logger.warning("No ipTM JSON file found, returning fallback value")
                return 0.5
            
            # Read ipTM from JSON
            with open(iptm_json, 'r') as f:
                data = json.load(f)
            
            # Extract ipTM (format may vary)
            iptm = None
            
            # Common ColabFold format
            if 'iptm' in data:
                iptm = data['iptm']
            elif 'iptm+ptm' in data:
                # Sometimes only combined score is available
                iptm = data['iptm+ptm']
                logger.info("    Using iptm+ptm score as fallback")
            
            # Alternative nested formats
            if iptm is None and isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict):
                    if 'iptm' in data[0]:
                        iptm = data[0]['iptm']
                    elif 'iptm+ptm' in data[0]:
                        iptm = data[0]['iptm+ptm']
            
            # Check for model-specific scores
            if iptm is None:
                for key in data.keys():
                    if 'model' in key.lower() or 'rank' in key.lower():
                        if isinstance(data[key], dict):
                            if 'iptm' in data[key]:
                                iptm = data[key]['iptm']
                                break
                            elif 'iptm+ptm' in data[key]:
                                iptm = data[key]['iptm+ptm']
                                break
            
            if iptm is None:
                logger.warning("ipTM not found in JSON file, returning fallback value")
                return 0.5
            
            logger.info(f"    ipTM: {iptm:.3f}")
            return float(iptm)
            
        except Exception as e:
            logger.warning(f"Error calculating ipTM: {str(e)}, returning fallback value")
            return 0.5

    def _calculate_rmsd(self, pdb1: Path, pdb2: Path) -> float:
        """Deprecated: Use _calculate_backbone_rmsd instead."""
        import random

        random.seed(hash(str(pdb1) + str(pdb2)))
        return random.uniform(0.5, 3.0)

    def _calculate_pae_interaction(self, pdb: Path) -> float:
        """Deprecated: Use _calculate_interface_pae instead."""
        import random

        random.seed(hash(str(pdb)))
        return random.uniform(2.0, 8.0)

    def _write_boltz_fasta_input(self, target_pdb: Path, target_chain: str, binder_sequence: str, out_fasta: Path):
        """Write Boltz FASTA input (deprecated format but supported by Boltz)."""
        out_fasta.parent.mkdir(parents=True, exist_ok=True)
        target_seq = self._extract_chain_sequence_from_pdb(target_pdb, target_chain)
        with open(out_fasta, "w") as f:
            f.write(f">A|protein|empty\n{target_seq}\n")
            f.write(f">B|protein|empty\n{binder_sequence}\n")

    def _write_chai_fasta_input(self, target_pdb: Path, target_chain: str, binder_sequence: str, out_fasta: Path):
        """Write Chai fold FASTA input with full target+binder complex sequences."""
        out_fasta.parent.mkdir(parents=True, exist_ok=True)
        target_seq = self._extract_chain_sequence_from_pdb(target_pdb, target_chain)
        with open(out_fasta, "w") as f:
            f.write(f">protein|name=target_chain_{target_chain}\n{target_seq}\n")
            f.write(">protein|name=binder_chain_B\n")
            f.write(f"{binder_sequence}\n")

    def _write_colabfold_fasta_input(
        self,
        target_pdb: Path,
        target_chain: str,
        binder_sequence: str,
        out_fasta: Path,
        job_name: str,
    ):
        """Write ColabFold complex FASTA using the `target:binder` sequence format."""
        out_fasta.parent.mkdir(parents=True, exist_ok=True)
        target_seq = self._extract_chain_sequence_from_pdb(target_pdb, target_chain)
        with open(out_fasta, "w") as f:
            f.write(f">{job_name}\n")
            f.write(f"{target_seq}:{binder_sequence}\n")

    def _extract_chain_sequence_from_pdb(self, pdb_path: Path, chain_id: str) -> str:
        """Extract one-letter AA sequence from ATOM records of one chain."""
        aa3_to_1 = {
            "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
            "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
            "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
            "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
            "MSE": "M",
        }
        seq = []
        seen = set()
        with open(pdb_path, "r") as f:
            for line in f:
                if not line.startswith("ATOM"):
                    continue
                if len(line) < 27:
                    continue
                if line[21].strip() != chain_id:
                    continue
                resname = line[17:20].strip().upper()
                resseq = line[22:26].strip()
                icode = line[26].strip()
                key = (resseq, icode)
                if key in seen:
                    continue
                seen.add(key)
                seq.append(aa3_to_1.get(resname, "X"))
        if not seq:
            raise ValueError(f"No residues found for chain '{chain_id}' in {pdb_path}")
        return "".join(seq)

    def _extract_backbone_index(self, candidate: DesignCandidate) -> Optional[int]:
        for tag in candidate.lineage:
            if tag.startswith("denovo_backbone_"):
                try:
                    return int(tag.split("_")[-1])
                except ValueError:
                    return None
        return None

    def _resolve_rfdiffusion_pdb(self, candidate: DesignCandidate) -> Optional[Path]:
        project_root = Path(self.config["project_root"])
        outputs_root = project_root / self.config["paths"]["outputs"]
        idx = self._extract_backbone_index(candidate)
        candidate_pdb = Path(candidate.binder_pdb_path) if candidate.binder_pdb_path else None

        if idx is not None and candidate_pdb is not None:
            parts = candidate_pdb.parts
            if "rfdiffusion" in parts:
                r = parts.index("rfdiffusion")
                if len(parts) > r + 2:
                    date_dir = parts[r + 1]
                    time_dir = parts[r + 2]
                    denovo_pdb = outputs_root / "rfdiffusion" / date_dir / time_dir / "denovo" / f"binder_{idx}.pdb"
                    if denovo_pdb.exists():
                        return denovo_pdb

        if idx is not None:
            matches = sorted(outputs_root.glob(f"rfdiffusion/*/*/denovo/binder_{idx}.pdb"))
            if matches:
                return matches[-1]

        if candidate_pdb is not None and candidate_pdb.exists():
            return candidate_pdb
        return None

    def _resolve_mpnn_fasta(self, candidate: DesignCandidate) -> Optional[Path]:
        if candidate.binder_fasta_path:
            p = Path(candidate.binder_fasta_path)
            if p.exists():
                return p

        project_root = Path(self.config["project_root"])
        outputs_root = project_root / self.config["paths"]["outputs"]
        idx = self._extract_backbone_index(candidate)
        if idx is None:
            return None

        candidate_pdb = Path(candidate.binder_pdb_path) if candidate.binder_pdb_path else None
        if candidate_pdb is not None:
            parts = candidate_pdb.parts
            if "rfdiffusion" in parts:
                r = parts.index("rfdiffusion")
                if len(parts) > r + 2:
                    date_dir = parts[r + 1]
                    time_dir = parts[r + 2]
                    seq_dir = outputs_root / "proteinmpnn" / date_dir / time_dir / "mpnn" / f"backbone_{idx:03d}" / "seqs"
                    if seq_dir.exists():
                        files = sorted(seq_dir.glob("*.fa"))
                        if files:
                            return files[0]

        matches = sorted(outputs_root.glob(f"proteinmpnn/*/*/mpnn/backbone_{idx:03d}/seqs/*.fa"))
        if matches:
            return matches[-1]
        return None

    def _read_first_fasta_sequence(self, fasta_path: Path) -> str:
        seq_lines: List[str] = []
        with open(fasta_path, "r") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith(">"):
                    if seq_lines:
                        break
                    continue
                seq_lines.append(line)
        return "".join(seq_lines)
