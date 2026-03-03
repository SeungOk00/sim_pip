"""
Phase 2: Evolutionary Generative Design
"""
from pathlib import Path
from typing import List
import logging

from ..models import DesignCandidate, PipelineState, RunRecord
from ..utils.tool_wrapper import RFdiffusionRunner, ProteinMPNNRunner
from ..utils.file_ops import ensure_dir, get_next_candidate_id
from datetime import datetime

logger = logging.getLogger(__name__)


class Phase2GenerativeDesign:
    """Phase 2: RFdiffusion + ProteinMPNN generation"""
    
    def __init__(self, config: dict):
        self.config = config
        self.phase_config = config['phase2']
        
        # Initialize tool runners
        dry_run = config.get('execution', {}).get('dry_run', False)
        self.rfdiffusion = RFdiffusionRunner(
            self.phase_config['rfdiffusion']['path'],
            dry_run=dry_run
        )
        self.proteinmpnn = ProteinMPNNRunner(
            self.phase_config['proteinmpnn']['path'],
            dry_run=dry_run
        )
    
    def run(self, state: PipelineState) -> PipelineState:
        """
        Run Phase 2: Generate binder candidates
        
        Pipeline:
        1. RFdiffusion de novo generation
        2. (Optional) RFdiffusion refinement
        3. ProteinMPNN sequence design
        
        Args:
            state: Current pipeline state with target specification
        
        Returns:
            Updated pipeline state with generated candidates
        """
        logger.info("=" * 80)
        logger.info("PHASE 2: Evolutionary Generative Design")
        logger.info("=" * 80)
        
        if state.target is None:
            raise ValueError("No target specification found. Run Phase 1 first.")
        
        # Setup directories
        project_root = Path(self.config['project_root'])
        run_dir = project_root / self.config['paths']['runs'] / state.run_id / "phase2_generate"
        ensure_dir(run_dir)
        
        candidates_dir = project_root / self.config['paths']['candidates']
        ensure_dir(candidates_dir)
        
        # Step 1: Generate de novo backbones
        logger.info("\nStep 1: RFdiffusion de novo generation")
        logger.info("-" * 80)
        backbones = self._generate_denovo_backbones(state, run_dir)
        logger.info(f"✓ Generated {len(backbones)} de novo backbones")
        
        # Step 2: (Optional) Refinement
        logger.info("\nStep 2: RFdiffusion refinement")
        logger.info("-" * 80)
        refined_backbones = self._refine_backbones(backbones, run_dir, state)
        logger.info(f"✓ Refined {len(refined_backbones)} backbones")
        
        # Step 3: Sequence design with ProteinMPNN
        logger.info("\nStep 3: ProteinMPNN sequence design")
        logger.info("-" * 80)
        candidates = self._design_sequences(refined_backbones, run_dir, state, candidates_dir)
        logger.info(f"✓ Generated {len(candidates)} sequence candidates")
        
        # Limit candidates
        max_candidates = self.phase_config.get('max_candidates_per_target', 100)
        if len(candidates) > max_candidates:
            logger.warning(f"Limiting candidates from {len(candidates)} to {max_candidates}")
            candidates = candidates[:max_candidates]
        
        # Update state
        state.candidates.extend(candidates)
        state.current_phase = "phase3_fast"
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"PHASE 2 COMPLETE")
        logger.info(f"Total candidates: {len(candidates)}")
        logger.info(f"{'=' * 80}\n")
        
        return state
    
    def _generate_denovo_backbones(self, state: PipelineState, run_dir: Path) -> List[Path]:
        """Generate de novo backbones with RFdiffusion"""
        target_pdb = Path(state.target.target_pdb_path)
        target_chain = state.target.chain_id
        hotspot_residues = state.target.hotspot_residues
        
        denovo_dir = run_dir / "denovo"
        ensure_dir(denovo_dir)
        
        num_designs = self.phase_config['rfdiffusion']['num_designs']
        T = self.phase_config['rfdiffusion']['de_novo_T']
        binder_length = self.phase_config['rfdiffusion'].get('binder_length', '70-100')
        noise_scale = self.phase_config['rfdiffusion'].get('noise_scale', 0.0)
        
        # Determine target residues range (simplified - use all for now)
        # In practice, you should crop the target around the binding site
        target_residues = "1-150"  # TODO: Calculate from PDB file
        
        logger.info(f"Target: {target_pdb}")
        logger.info(f"Target chain: {target_chain}")
        logger.info(f"Target residues: {target_residues}")
        logger.info(f"Hotspots: {hotspot_residues}")
        logger.info(f"Binder length: {binder_length}")
        logger.info(f"Generating {num_designs} designs with T={T}, noise={noise_scale}")
        
        start_time = datetime.now()
        
        try:
            backbones = self.rfdiffusion.generate_binder(
                target_pdb=target_pdb,
                target_chain=target_chain,
                target_residues=target_residues,
                hotspot_residues=hotspot_residues,
                binder_length=binder_length,
                output_dir=denovo_dir,
                num_designs=num_designs,
                T=T,
                noise_scale=noise_scale
            )
            
            # Record execution
            record = RunRecord(
                tool_name="RFdiffusion",
                tool_version="1.0",
                command=f"generate_binder T={T} num={num_designs} binder_length={binder_length}",
                inputs={
                    "target_pdb": str(target_pdb),
                    "target_chain": target_chain,
                    "target_residues": target_residues,
                    "hotspots": hotspot_residues,
                    "binder_length": binder_length
                },
                outputs={"backbones": [str(b) for b in backbones]},
                start_time=start_time.isoformat(),
                end_time=datetime.now().isoformat(),
                exit_code=0
            )
            state.add_run_record(record)
            
            return backbones
            
        except Exception as e:
            logger.error(f"RFdiffusion generation failed: {str(e)}")
            raise
    
    def _refine_backbones(self, backbones: List[Path], run_dir: Path, 
                         state: PipelineState) -> List[Path]:
        """Refine backbones with RFdiffusion"""
        refine_dir = run_dir / "refinement"
        ensure_dir(refine_dir)
        
        T = self.phase_config['rfdiffusion']['refinement_T']
        max_iterations = self.phase_config['rfdiffusion']['max_refinement_iterations']
        
        refined = []
        
        for i, backbone in enumerate(backbones):
            logger.info(f"Refining backbone {i+1}/{len(backbones)}: {backbone.name}")
            
            current_backbone = backbone
            
            for iteration in range(max_iterations):
                try:
                    iter_dir = refine_dir / f"backbone_{i:03d}_iter_{iteration}"
                    ensure_dir(iter_dir)
                    
                    refined_backbone = self.rfdiffusion.refine(
                        input_pdb=current_backbone,
                        output_dir=iter_dir,
                        T=T
                    )
                    
                    current_backbone = refined_backbone
                    
                except Exception as e:
                    logger.warning(f"Refinement iteration {iteration} failed: {str(e)}")
                    break
            
            refined.append(current_backbone)
        
        return refined
    
    def _design_sequences(self, backbones: List[Path], run_dir: Path,
                         state: PipelineState, candidates_dir: Path) -> List[DesignCandidate]:
        """Design sequences with ProteinMPNN"""
        mpnn_dir = run_dir / "mpnn"
        ensure_dir(mpnn_dir)
        
        num_seq_per_target = self.phase_config['proteinmpnn']['num_seq_per_target']
        temps = self.phase_config['proteinmpnn']['sampling_temps']
        
        candidates = []
        
        for i, backbone in enumerate(backbones):
            logger.info(f"Designing sequences for backbone {i+1}/{len(backbones)}")
            
            backbone_dir = mpnn_dir / f"backbone_{i:03d}"
            ensure_dir(backbone_dir)
            
            try:
                sequences = self.proteinmpnn.design_sequence(
                    backbone_pdb=backbone,
                    output_dir=backbone_dir,
                    num_seqs=num_seq_per_target,
                    temps=temps
                )
                
                # Create candidate for each sequence
                for j, sequence in enumerate(sequences):
                    candidate_id = get_next_candidate_id(candidates_dir)
                    
                    candidate = DesignCandidate(
                        candidate_id=candidate_id,
                        parent_id=None,
                        binder_sequence=sequence,
                        binder_pdb_path=str(backbone),
                        stage="generated",
                        lineage=[f"denovo_backbone_{i}", f"mpnn_seq_{j}"]
                    )
                    
                    # Save candidate
                    candidate.save(candidates_dir)
                    candidates.append(candidate)
                    
            except Exception as e:
                logger.error(f"ProteinMPNN failed for backbone {i}: {str(e)}")
                continue
        
        return candidates
