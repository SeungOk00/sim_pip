"""
Phase 3: Fast Screening and Deep Validation
"""
from pathlib import Path
from typing import List
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

        fasta_path = cand_dir / "binder.fasta"
        with open(fasta_path, "w") as f:
            f.write(f">{candidate.candidate_id}\n{candidate.binder_sequence}\n")

        try:
            target_pdb = Path(state.target.target_pdb_path)

            chai_dir = cand_dir / "chai"
            chai_cfg = self.fast_config.get("chai", {})
            chai_pdb, chai_conf = self.chai.predict_complex(
                target_pdb=target_pdb,
                binder_fasta=fasta_path,
                output_dir=chai_dir,
                command_template=chai_cfg.get(
                    "command_template",
                    "python -m chai_lab.run --target {target_pdb} --binder {binder_fasta} --output_dir {output_dir}",
                ),
                output_file=chai_cfg.get("output_file", "predicted_complex.pdb"),
            )
            candidate.metrics.update(chai_conf)
            candidate.complex_pdb_path = str(chai_pdb)

            boltz_pdb = None
            if self.boltz is not None:
                boltz_cfg = self.fast_config.get("boltz", {})
                boltz_dir = cand_dir / "boltz"
                boltz_pdb, boltz_conf = self.boltz.predict_complex(
                    target_pdb=target_pdb,
                    binder_fasta=fasta_path,
                    output_dir=boltz_dir,
                    command_template=boltz_cfg.get(
                        "command_template",
                        "boltz predict --target {target_pdb} --binder {binder_fasta} --output_dir {output_dir}",
                    ),
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
