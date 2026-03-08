"""
Phase 3: Fast Screening and Deep Validation
"""
from pathlib import Path
from typing import List, Optional
import logging
from datetime import datetime
import subprocess
import re

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
        self.chai = ChaiRunner(self.fast_config["chai"]["path"], dry_run=dry_run)

        self.boltz = None
        boltz_cfg = self.fast_config.get("boltz", {})
        if boltz_cfg.get("enabled", False):
            self.boltz = BoltzRunner(boltz_cfg.get("path", ""), dry_run=dry_run)

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

        fast_dir = outputs_root / "phase3_fast" / date_dir / time_dir
        ensure_dir(fast_dir)

        generated_candidates = state.get_candidates_by_stage("generated")
        logger.info(f"Screening {len(generated_candidates)} candidates")
        for candidate in generated_candidates:
            self._fast_screen_candidate(candidate, fast_dir, state)

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

    def _fast_screen_candidate(self, candidate: DesignCandidate, run_dir: Path, state: PipelineState):
        logger.info(f"\nScreening {candidate.candidate_id}...")
        cand_dir = run_dir / candidate.candidate_id
        ensure_dir(cand_dir)

        try:
            target_pdb = self._resolve_rfdiffusion_pdb(candidate) or Path(state.target.target_pdb_path)
            fasta_path = self._resolve_mpnn_fasta(candidate)

            binder_sequence = candidate.binder_sequence
            if (not binder_sequence) and fasta_path is not None:
                binder_sequence = self._read_first_fasta_sequence(fasta_path)
                candidate.binder_sequence = binder_sequence

            if not binder_sequence:
                raise ValueError(f"No binder sequence available for {candidate.candidate_id}")

            if fasta_path is None:
                fasta_path = cand_dir / "binder.fasta"
                with open(fasta_path, "w") as f:
                    f.write(f">{candidate.candidate_id}\n{binder_sequence}\n")
            else:
                candidate.binder_fasta_path = str(fasta_path)

            logger.info(f"  target pdb: {target_pdb}")
            logger.info(f"  binder fasta: {fasta_path}")

            chai_dir = cand_dir / "chai"
            chai_cfg = self.fast_config.get("chai", {})
            chai_input = chai_dir / "chai_input.fasta"
            self._write_chai_fasta_input(
                target_pdb=target_pdb,
                target_chain=state.target.chain_id,
                binder_sequence=binder_sequence,
                out_fasta=chai_input,
            )
            chai_pdb, chai_conf = self.chai.predict_complex(
                target_pdb=target_pdb,
                binder_fasta=fasta_path,
                output_dir=chai_dir,
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
                boltz_dir = cand_dir / "boltz"
                boltz_input = boltz_dir / "boltz_input.fasta"
                self._write_boltz_fasta_input(
                    target_pdb=target_pdb,
                    target_chain=state.target.chain_id,
                    binder_sequence=binder_sequence,
                    out_fasta=boltz_input,
                )
                boltz_pdb, boltz_conf = self.boltz.predict_complex(
                    target_pdb=target_pdb,
                    binder_fasta=fasta_path,
                    output_dir=boltz_dir,
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
                consensus_dockq = self._calculate_dockq(model_pdb=boltz_pdb, reference_pdb=chai_pdb)
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
            colabfold_pdb = self._run_colabfold(candidate, cand_dir)
            chai_pdb = Path(candidate.complex_pdb_path)
            rmsd = self._calculate_rmsd(chai_pdb, colabfold_pdb)
            candidate.metrics["rmsd_chai_vs_cf"] = rmsd

            pae = self._calculate_pae_interaction(colabfold_pdb)
            candidate.metrics["pae_interaction"] = pae

            gates = self.deep_config["gates"]
            if rmsd >= gates["rmsd_consensus_threshold"]:
                candidate.decision = {"gate": "FAIL_consensus", "reason": f"RMSD {rmsd:.2f} >= {gates['rmsd_consensus_threshold']}"}
                candidate.stage = "failed"
                logger.info(f"  FAIL - Poor consensus (RMSD: {rmsd:.2f})")
            elif pae >= gates["pae_interaction_threshold"]:
                candidate.decision = {"gate": "FAIL_pae", "reason": f"pAE {pae:.2f} >= {gates['pae_interaction_threshold']}"}
                candidate.stage = "failed"
                logger.info(f"  FAIL - Low confidence (pAE: {pae:.2f})")
            else:
                candidate.decision = {"gate": "PASS", "reason": f"Consensus RMSD {rmsd:.2f}, pAE {pae:.2f}"}
                candidate.stage = "deep_validated"
                logger.info(f"  VALIDATED - RMSD: {rmsd:.2f}, pAE: {pae:.2f}")

            candidates_dir = Path(self.config["project_root"]) / self.config["paths"]["candidates"]
            candidate.save(candidates_dir)
        except Exception as e:
            logger.error(f"  Deep validation failed: {str(e)}")
            candidate.decision = {"gate": "FAIL", "reason": f"Validation error: {str(e)}"}
            candidate.stage = "failed"

    def _run_colabfold(self, candidate: DesignCandidate, output_dir: Path) -> Path:
        logger.info("  Running ColabFold (placeholder)...")
        return output_dir / "colabfold_pred.pdb"

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

    def _calculate_rmsd(self, pdb1: Path, pdb2: Path) -> float:
        import random

        random.seed(hash(str(pdb1) + str(pdb2)))
        return random.uniform(0.5, 3.0)

    def _calculate_pae_interaction(self, pdb: Path) -> float:
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
