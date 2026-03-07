"""
Phase 3: Fast Screening and Deep Validation
"""
from pathlib import Path
from typing import List, Dict, Tuple
import logging

from ..models import DesignCandidate, PipelineState, RunRecord
from ..utils.tool_wrapper import ChaiRunner
from ..utils.file_ops import ensure_dir
from datetime import datetime

logger = logging.getLogger(__name__)


class Phase3ScreeningAndValidation:
    """Phase 3: Fast screening + Deep validation"""
    
    def __init__(self, config: dict):
        self.config = config
        self.fast_config = config['phase3_fast']
        self.deep_config = config['phase3_deep']
        
        # Initialize tool runners
        dry_run = config.get('execution', {}).get('dry_run', False)
        self.chai = ChaiRunner(
            self.fast_config['chai']['path'],
            dry_run=dry_run
        )
    
    def run(self, state: PipelineState) -> PipelineState:
        """
        Run Phase 3: Screen and validate candidates
        
        Pipeline:
        1. Fast screening (Chai-1, DockQ, CAPRI-Q)
        2. Gate decision (FAIL/REFINE/PASS)
        3. Deep validation (ColabFold) for PASS candidates
        
        Args:
            state: Current pipeline state with generated candidates
        
        Returns:
            Updated pipeline state with screened candidates
        """
        logger.info("=" * 80)
        logger.info("PHASE 3: Screening and Validation")
        logger.info("=" * 80)
        
        # Setup directories
        project_root = Path(self.config['project_root'])
        now = datetime.now()
        date_dir = now.strftime("%Y-%m-%d")
        time_dir = now.strftime("%H-%M-%S")
        outputs_root = project_root / self.config['paths']['outputs']
        
        # Phase 3-A: Fast screening
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3-A: Fast Screening")
        logger.info("=" * 80)
        
        fast_dir = outputs_root / "chai" / date_dir / time_dir / "phase3_fast"
        ensure_dir(fast_dir)
        
        generated_candidates = state.get_candidates_by_stage("generated")
        logger.info(f"Screening {len(generated_candidates)} candidates")
        
        for candidate in generated_candidates:
            self._fast_screen_candidate(candidate, fast_dir, state)
        
        # Count results
        passed = state.get_candidates_by_stage("fast_screened")
        failed = [c for c in state.candidates if c.decision.get("gate") == "FAIL"]
        refine = [c for c in state.candidates if c.decision.get("gate") == "REFINE"]
        
        logger.info(f"\nFast Screening Results:")
        logger.info(f"  PASS: {len(passed)} candidates")
        logger.info(f"  REFINE: {len(refine)} candidates")
        logger.info(f"  FAIL: {len(failed)} candidates")
        
        # Phase 3-B: Deep validation
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3-B: Deep Validation")
        logger.info("=" * 80)
        
        deep_dir = outputs_root / "colabfold" / date_dir / time_dir / "phase3_deep"
        ensure_dir(deep_dir)
        
        logger.info(f"Deep validating {len(passed)} candidates")
        
        for candidate in passed:
            self._deep_validate_candidate(candidate, deep_dir, state)
        
        validated = state.get_candidates_by_stage("deep_validated")
        
        logger.info(f"\nDeep Validation Results:")
        logger.info(f"  VALIDATED: {len(validated)} candidates")
        
        # Update state
        state.current_phase = "phase4"
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"PHASE 3 COMPLETE")
        logger.info(f"Candidates passing to Phase 4: {len(validated)}")
        logger.info(f"{'=' * 80}\n")
        
        return state
    
    def _fast_screen_candidate(self, candidate: DesignCandidate, 
                               run_dir: Path, state: PipelineState):
        """Run fast screening on a single candidate"""
        logger.info(f"\nScreening {candidate.candidate_id}...")
        
        cand_dir = run_dir / candidate.candidate_id
        ensure_dir(cand_dir)
        
        # Create FASTA file for binder
        fasta_path = cand_dir / "binder.fasta"
        with open(fasta_path, 'w') as f:
            f.write(f">{candidate.candidate_id}\n{candidate.binder_sequence}\n")
        
        # Run Chai-1 structure prediction
        try:
            target_pdb = Path(state.target.target_pdb_path)
            
            complex_pdb, confidence = self.chai.predict_complex(
                target_pdb=target_pdb,
                binder_fasta=fasta_path,
                output_dir=cand_dir
            )
            
            # Update candidate
            candidate.complex_pdb_path = str(complex_pdb)
            candidate.metrics.update(confidence)
            
            # Calculate DockQ (placeholder - actual implementation needed)
            dockq_score = self._calculate_dockq(complex_pdb, target_pdb)
            candidate.metrics['dockq'] = dockq_score
            
            # Gate decision
            gates = self.fast_config['gates']
            
            if dockq_score < gates['fail_threshold']:
                candidate.decision = {
                    "gate": "FAIL",
                    "reason": f"DockQ {dockq_score:.3f} < {gates['fail_threshold']}"
                }
                candidate.stage = "failed"
                logger.info(f"  ❌ FAIL - DockQ: {dockq_score:.3f}")
                
            elif dockq_score < gates['refine_threshold']:
                candidate.decision = {
                    "gate": "REFINE",
                    "reason": f"DockQ {dockq_score:.3f} needs refinement"
                }
                candidate.stage = "refine_queue"
                logger.info(f"  🔄 REFINE - DockQ: {dockq_score:.3f}")
                
            else:
                candidate.decision = {
                    "gate": "PASS",
                    "reason": f"DockQ {dockq_score:.3f} >= {gates['pass_threshold']}"
                }
                candidate.stage = "fast_screened"
                logger.info(f"  ✓ PASS - DockQ: {dockq_score:.3f}")
            
            # Save updated candidate
            candidates_dir = Path(self.config['project_root']) / self.config['paths']['candidates']
            candidate.save(candidates_dir)
            
        except Exception as e:
            logger.error(f"  ❌ Fast screening failed: {str(e)}")
            candidate.decision = {
                "gate": "FAIL",
                "reason": f"Tool error: {str(e)}"
            }
            candidate.stage = "failed"
    
    def _deep_validate_candidate(self, candidate: DesignCandidate,
                                 run_dir: Path, state: PipelineState):
        """Run deep validation with ColabFold"""
        logger.info(f"\nValidating {candidate.candidate_id}...")
        
        cand_dir = run_dir / candidate.candidate_id
        ensure_dir(cand_dir)
        
        try:
            # Run ColabFold (placeholder - actual implementation needed)
            colabfold_pdb = self._run_colabfold(candidate, cand_dir)
            
            # Calculate consensus RMSD
            chai_pdb = Path(candidate.complex_pdb_path)
            rmsd = self._calculate_rmsd(chai_pdb, colabfold_pdb)
            candidate.metrics['rmsd_chai_vs_cf'] = rmsd
            
            # Calculate pAE interaction (placeholder)
            pae = self._calculate_pae_interaction(colabfold_pdb)
            candidate.metrics['pae_interaction'] = pae
            
            # Gate decision
            gates = self.deep_config['gates']
            
            if rmsd >= gates['rmsd_consensus_threshold']:
                candidate.decision = {
                    "gate": "FAIL_consensus",
                    "reason": f"RMSD {rmsd:.2f} >= {gates['rmsd_consensus_threshold']}"
                }
                candidate.stage = "failed"
                logger.info(f"  ❌ FAIL - Poor consensus (RMSD: {rmsd:.2f} Å)")
                
            elif pae >= gates['pae_interaction_threshold']:
                candidate.decision = {
                    "gate": "FAIL_pae",
                    "reason": f"pAE {pae:.2f} >= {gates['pae_interaction_threshold']}"
                }
                candidate.stage = "failed"
                logger.info(f"  ❌ FAIL - Low confidence (pAE: {pae:.2f})")
                
            else:
                candidate.decision = {
                    "gate": "PASS",
                    "reason": f"Consensus RMSD {rmsd:.2f} Å, pAE {pae:.2f}"
                }
                candidate.stage = "deep_validated"
                logger.info(f"  ✓ VALIDATED - RMSD: {rmsd:.2f} Å, pAE: {pae:.2f}")
            
            # Save updated candidate
            candidates_dir = Path(self.config['project_root']) / self.config['paths']['candidates']
            candidate.save(candidates_dir)
            
        except Exception as e:
            logger.error(f"  ❌ Deep validation failed: {str(e)}")
            candidate.decision = {
                "gate": "FAIL",
                "reason": f"Validation error: {str(e)}"
            }
            candidate.stage = "failed"
    
    def _calculate_dockq(self, complex_pdb: Path, target_pdb: Path) -> float:
        """
        Calculate DockQ score
        Placeholder - actual implementation should use DockQ tool
        """
        import random
        random.seed(hash(str(complex_pdb)))
        return random.uniform(0.1, 0.9)
    
    def _run_colabfold(self, candidate: DesignCandidate, output_dir: Path) -> Path:
        """
        Run ColabFold prediction
        Placeholder - actual implementation needed
        """
        logger.info("  Running ColabFold (placeholder)...")
        output_pdb = output_dir / "colabfold_pred.pdb"
        # Actual implementation would run ColabFold here
        return output_pdb
    
    def _calculate_rmsd(self, pdb1: Path, pdb2: Path) -> float:
        """
        Calculate RMSD between two structures
        Placeholder - actual implementation should use structural alignment tool
        """
        import random
        random.seed(hash(str(pdb1)))
        return random.uniform(0.5, 3.0)
    
    def _calculate_pae_interaction(self, pdb: Path) -> float:
        """
        Calculate pAE interaction score
        Placeholder - actual implementation needed
        """
        import random
        random.seed(hash(str(pdb)))
        return random.uniform(2.0, 8.0)
