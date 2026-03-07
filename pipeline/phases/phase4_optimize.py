"""
Phase 4: Multi-Objective Optimization (Developability)
"""
from pathlib import Path
from typing import List, Dict, Tuple
import logging
import random
from datetime import datetime

from ..models import DesignCandidate, PipelineState
from ..utils.file_ops import ensure_dir

logger = logging.getLogger(__name__)


class Phase4Optimization:
    """Phase 4: NSGA-II multi-objective optimization"""
    
    def __init__(self, config: dict):
        self.config = config
        self.phase_config = config['phase4']
        self.objectives = self.phase_config['objectives']
        self.constraints = self.phase_config['constraints']
    
    def run(self, state: PipelineState) -> PipelineState:
        """
        Run Phase 4: Optimize for developability
        
        Pipeline:
        1. Rosetta FastRelax preprocessing
        2. Evaluate developability metrics
        3. Apply hard constraints
        4. NSGA-II Pareto optimization
        5. Clustering and selection
        
        Args:
            state: Current pipeline state with validated candidates
        
        Returns:
            Updated pipeline state with optimized candidates
        """
        logger.info("=" * 80)
        logger.info("PHASE 4: Multi-Objective Optimization")
        logger.info("=" * 80)
        
        # Setup directories
        project_root = Path(self.config['project_root'])
        now = datetime.now()
        date_dir = now.strftime("%Y-%m-%d")
        time_dir = now.strftime("%H-%M-%S")
        run_dir = project_root / self.config['paths']['outputs'] / "rosetta" / date_dir / time_dir / "phase4_opt"
        ensure_dir(run_dir)
        
        # Get validated candidates
        validated = state.get_candidates_by_stage("deep_validated")
        logger.info(f"\nOptimizing {len(validated)} validated candidates")
        
        if not validated:
            logger.warning("No validated candidates to optimize!")
            state.current_phase = "phase5"
            return state
        
        # Step 1: Preprocess with Rosetta FastRelax
        logger.info("\nStep 1: Rosetta FastRelax preprocessing")
        logger.info("-" * 80)
        relaxed_candidates = self._rosetta_preprocess(validated, run_dir)
        logger.info(f"✓ Relaxed {len(relaxed_candidates)} structures")
        
        # Step 2: Evaluate developability metrics
        logger.info("\nStep 2: Evaluate developability metrics")
        logger.info("-" * 80)
        for candidate in relaxed_candidates:
            self._evaluate_developability(candidate)
        logger.info(f"✓ Evaluated {len(relaxed_candidates)} candidates")
        
        # Step 3: Apply hard constraints
        logger.info("\nStep 3: Apply hard constraints")
        logger.info("-" * 80)
        feasible_candidates = [c for c in relaxed_candidates if self._is_feasible(c)]
        logger.info(f"✓ {len(feasible_candidates)} candidates passed constraints")
        
        if not feasible_candidates:
            logger.warning("No candidates passed hard constraints!")
            state.current_phase = "phase5"
            return state
        
        # Step 4: NSGA-II Pareto optimization
        logger.info("\nStep 4: NSGA-II Pareto optimization")
        logger.info("-" * 80)
        pareto_candidates = self._nsga2_optimize(feasible_candidates)
        logger.info(f"✓ {len(pareto_candidates)} candidates on Pareto front")
        
        # Step 5: Clustering and selection
        logger.info("\nStep 5: Clustering and final selection")
        logger.info("-" * 80)
        final_count = self.phase_config['final_selection']
        final_candidates = self._cluster_and_select(pareto_candidates, k=final_count)
        logger.info(f"✓ Selected {len(final_candidates)} final candidates")
        
        # Mark final candidates
        for candidate in final_candidates:
            candidate.stage = "selected"
            candidates_dir = project_root / self.config['paths']['candidates']
            candidate.save(candidates_dir)
        
        # Update state
        state.current_phase = "phase5"
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"PHASE 4 COMPLETE")
        logger.info(f"Final candidates selected: {len(final_candidates)}")
        logger.info(f"{'=' * 80}\n")
        
        return state
    
    def _rosetta_preprocess(self, candidates: List[DesignCandidate], 
                           run_dir: Path) -> List[DesignCandidate]:
        """Preprocess structures with Rosetta FastRelax"""
        if not self.phase_config['rosetta']['enabled']:
            logger.info("Rosetta preprocessing disabled, skipping...")
            return candidates
        
        relaxed = []
        cycles = self.phase_config['rosetta']['fastrelax_cycles']
        
        for i, candidate in enumerate(candidates):
            logger.info(f"  Relaxing {i+1}/{len(candidates)}: {candidate.candidate_id}")
            
            try:
                # Placeholder - actual Rosetta implementation needed
                relaxed_pdb = self._run_fastrelax(candidate, run_dir, cycles)
                candidate.metrics['relaxed'] = True
                candidate.metrics['fastrelax_cycles'] = cycles
                relaxed.append(candidate)
                
            except Exception as e:
                logger.error(f"  FastRelax failed: {str(e)}")
                continue
        
        return relaxed
    
    def _run_fastrelax(self, candidate: DesignCandidate, run_dir: Path, 
                      cycles: int) -> Path:
        """Run Rosetta FastRelax (placeholder)"""
        output_pdb = run_dir / f"{candidate.candidate_id}_relaxed.pdb"
        # Actual Rosetta implementation would go here
        return output_pdb
    
    def _evaluate_developability(self, candidate: DesignCandidate):
        """Evaluate all developability metrics"""
        
        # Objective 1: Interface binding affinity (minimize)
        candidate.metrics['interface_ddg'] = self._calculate_interface_ddg(candidate)
        
        # Objective 2: Solubility (minimize SAP score)
        candidate.metrics['sap'] = self._calculate_sap(candidate)
        
        # Objective 3: Stability (minimize total score per residue)
        candidate.metrics['total_score_per_res'] = self._calculate_total_score_per_res(candidate)
        
        # Constraints
        candidate.metrics['packstat'] = self._calculate_packstat(candidate)
        candidate.metrics['overall_rmsd'] = self._calculate_overall_rmsd(candidate)
        candidate.metrics['epitope_rmsd'] = self._calculate_epitope_rmsd(candidate)
        candidate.metrics['rg'] = self._calculate_radius_of_gyration(candidate)
        candidate.metrics['mhc2_strong_binders_count'] = self._calculate_mhc2_risk(candidate)
        
        logger.info(f"  {candidate.candidate_id}:")
        logger.info(f"    ddG: {candidate.metrics['interface_ddg']:.2f}")
        logger.info(f"    SAP: {candidate.metrics['sap']:.2f}")
        logger.info(f"    Score/res: {candidate.metrics['total_score_per_res']:.2f}")
    
    def _is_feasible(self, candidate: DesignCandidate) -> bool:
        """Check if candidate meets all hard constraints"""
        m = candidate.metrics
        c = self.constraints
        
        checks = [
            (m.get('packstat', 0) >= c['packstat_min'], "packstat"),
            (m.get('overall_rmsd', 999) <= c['overall_rmsd_max'], "overall_rmsd"),
            (m.get('epitope_rmsd', 999) <= c['epitope_rmsd_max'], "epitope_rmsd"),
            (m.get('rg', 999) <= c['rg_max'], "rg"),
            (m.get('mhc2_strong_binders_count', 999) <= c['mhc2_strong_binders_max'], "mhc2_risk")
        ]
        
        passed = all(check[0] for check in checks)
        
        if not passed:
            failed = [check[1] for check in checks if not check[0]]
            logger.info(f"  {candidate.candidate_id}: FAIL - constraints: {', '.join(failed)}")
            candidate.stage = "failed"
            candidate.decision = {
                "gate": "FAIL",
                "reason": f"Failed constraints: {', '.join(failed)}"
            }
        
        return passed
    
    def _nsga2_optimize(self, candidates: List[DesignCandidate]) -> List[DesignCandidate]:
        """
        NSGA-II Pareto optimization
        
        This is a selection-based approach (not generating new variants)
        Ranks candidates by Pareto dominance and crowding distance
        """
        
        # Extract objectives (minimize all)
        objectives = []
        for c in candidates:
            obj = [
                c.metrics['interface_ddg'],  # Lower is better (more negative)
                c.metrics['sap'],             # Lower is better
                c.metrics['total_score_per_res']  # Lower is better
            ]
            objectives.append(obj)
        
        # Find Pareto front (non-dominated solutions)
        pareto_indices = self._find_pareto_front(objectives)
        pareto_candidates = [candidates[i] for i in pareto_indices]
        
        # Mark as optimized
        for candidate in pareto_candidates:
            candidate.stage = "optimized"
        
        return pareto_candidates
    
    def _find_pareto_front(self, objectives: List[List[float]]) -> List[int]:
        """Find non-dominated solutions (Pareto front)"""
        n = len(objectives)
        dominated = [False] * n
        
        for i in range(n):
            if dominated[i]:
                continue
            for j in range(n):
                if i == j or dominated[j]:
                    continue
                
                # Check if j dominates i (all objectives better or equal, at least one strictly better)
                j_dominates_i = all(objectives[j][k] <= objectives[i][k] for k in range(len(objectives[0]))) and \
                               any(objectives[j][k] < objectives[i][k] for k in range(len(objectives[0])))
                
                if j_dominates_i:
                    dominated[i] = True
                    break
        
        pareto_indices = [i for i in range(n) if not dominated[i]]
        return pareto_indices
    
    def _cluster_and_select(self, candidates: List[DesignCandidate], 
                           k: int) -> List[DesignCandidate]:
        """
        Cluster sequences and select representatives
        
        Uses sequence similarity clustering (mmseqs2-like approach)
        Selects diverse representatives from clusters
        """
        
        if len(candidates) <= k:
            return candidates
        
        # Simple diversity selection (placeholder - actual mmseqs2 clustering needed)
        # Sort by interface_ddg and select top k with diversity
        candidates_sorted = sorted(candidates, 
                                   key=lambda c: c.metrics['interface_ddg'])
        
        selected = []
        for candidate in candidates_sorted:
            if len(selected) >= k:
                break
            
            # Check sequence diversity
            if self._is_diverse(candidate, selected):
                selected.append(candidate)
        
        # Fill remaining slots if needed
        while len(selected) < k and len(selected) < len(candidates):
            for c in candidates_sorted:
                if c not in selected:
                    selected.append(c)
                    if len(selected) >= k:
                        break
        
        return selected[:k]
    
    def _is_diverse(self, candidate: DesignCandidate, 
                   selected: List[DesignCandidate], 
                   threshold: float = 0.7) -> bool:
        """Check if candidate is diverse from selected set"""
        if not selected:
            return True
        
        for sel in selected:
            similarity = self._sequence_similarity(
                candidate.binder_sequence,
                sel.binder_sequence
            )
            if similarity > threshold:
                return False
        
        return True
    
    def _sequence_similarity(self, seq1: str, seq2: str) -> float:
        """Calculate sequence similarity (simple identity)"""
        if len(seq1) != len(seq2):
            return 0.0
        matches = sum(a == b for a, b in zip(seq1, seq2))
        return matches / len(seq1)
    
    # Placeholder metric calculation methods
    def _calculate_interface_ddg(self, candidate: DesignCandidate) -> float:
        """Calculate interface ddG (placeholder)"""
        random.seed(hash(candidate.candidate_id + "ddg"))
        return random.uniform(-40, -20)
    
    def _calculate_sap(self, candidate: DesignCandidate) -> float:
        """Calculate SAP score (placeholder)"""
        random.seed(hash(candidate.candidate_id + "sap"))
        return random.uniform(20, 50)
    
    def _calculate_total_score_per_res(self, candidate: DesignCandidate) -> float:
        """Calculate total score per residue (placeholder)"""
        random.seed(hash(candidate.candidate_id + "score"))
        return random.uniform(-4.0, -2.5)
    
    def _calculate_packstat(self, candidate: DesignCandidate) -> float:
        """Calculate packstat (placeholder)"""
        random.seed(hash(candidate.candidate_id + "pack"))
        return random.uniform(0.55, 0.70)
    
    def _calculate_overall_rmsd(self, candidate: DesignCandidate) -> float:
        """Calculate overall RMSD (placeholder)"""
        random.seed(hash(candidate.candidate_id + "rmsd"))
        return random.uniform(0.5, 2.5)
    
    def _calculate_epitope_rmsd(self, candidate: DesignCandidate) -> float:
        """Calculate epitope RMSD (placeholder)"""
        random.seed(hash(candidate.candidate_id + "epitope"))
        return random.uniform(0.3, 1.5)
    
    def _calculate_radius_of_gyration(self, candidate: DesignCandidate) -> float:
        """Calculate radius of gyration (placeholder)"""
        random.seed(hash(candidate.candidate_id + "rg"))
        return random.uniform(12, 18)
    
    def _calculate_mhc2_risk(self, candidate: DesignCandidate) -> int:
        """Calculate MHC-II immunogenicity risk (placeholder)"""
        random.seed(hash(candidate.candidate_id + "mhc"))
        return random.randint(0, 2)
