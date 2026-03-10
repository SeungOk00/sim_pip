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
        now = datetime.now()
        date_dir = now.strftime("%Y-%m-%d")
        time_dir = now.strftime("%H-%M-%S")
        outputs_root = project_root / self.config['paths']['outputs']
        rfdiffusion_out_dir = outputs_root / "rfdiffusion" / date_dir / time_dir
        proteinmpnn_out_dir = outputs_root / "proteinmpnn" / date_dir / time_dir
        ensure_dir(rfdiffusion_out_dir)
        ensure_dir(proteinmpnn_out_dir)
        
        candidates_dir = project_root / self.config['paths']['candidates']
        ensure_dir(candidates_dir)
        
        # Step 1: Generate de novo backbones
        logger.info("\nStep 1: RFdiffusion de novo generation")
        logger.info("-" * 80)
        backbones = self._generate_denovo_backbones(state, rfdiffusion_out_dir)
        logger.info(f"Generated {len(backbones)} de novo backbones")
        
        # Step 2: (Optional) Refinement
        logger.info("\nStep 2: RFdiffusion refinement")
        logger.info("-" * 80)
        refined_backbones = self._refine_backbones(backbones, rfdiffusion_out_dir, state)
        logger.info(f"Refined {len(refined_backbones)} backbones")
        
        # Step 3: Sequence design with ProteinMPNN
        logger.info("\nStep 3: ProteinMPNN sequence design")
        logger.info("-" * 80)
        candidates = self._design_sequences(refined_backbones, proteinmpnn_out_dir, state, candidates_dir)
        logger.info(f"Generated {len(candidates)} sequence candidates")
        
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
    
    def _generate_denovo_backbones(self, state: PipelineState, tool_out_dir: Path) -> List[Path]:
        """Generate de novo backbones with RFdiffusion"""
        target_pdb = Path(state.target.target_pdb_path)
        target_chain = state.target.chain_id
        hotspot_residues = state.target.hotspot_residues
        
        denovo_dir = tool_out_dir / "denovo"
        ensure_dir(denovo_dir)
        
        num_designs = self.phase_config['rfdiffusion']['num_designs']
        T = self.phase_config['rfdiffusion']['de_novo_T']
        target_residues = self.phase_config['rfdiffusion'].get('target_residues', '')
        binder_length = self.phase_config['rfdiffusion'].get('binder_length', '')
        noise_scale = self.phase_config['rfdiffusion'].get('noise_scale', 0.0)
        output_prefix = self.phase_config['rfdiffusion'].get('output_prefix', 'binder')

        # If user did not provide these, do not pass them to RFdiffusion.
        target_residues = target_residues if str(target_residues).strip() else None
        binder_length = binder_length if str(binder_length).strip() else None
        
        logger.info(f"Target: {target_pdb}")
        logger.info(f"Target chain: {target_chain}")
        logger.info(f"Target residues: {target_residues if target_residues else '(Hydra default)'}")
        logger.info(f"Hotspots: {hotspot_residues}")
        logger.info(f"Binder length: {binder_length if binder_length else '(Hydra default)'}")
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
                noise_scale=noise_scale,
                output_prefix=output_prefix
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
                    "binder_length": binder_length,
                    "output_prefix": output_prefix
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
    
    def _refine_backbones(self, backbones: List[Path], tool_out_dir: Path, 
                         state: PipelineState) -> List[Path]:
        """Refine backbones with RFdiffusion"""
        refine_dir = tool_out_dir / "refinement"
        ensure_dir(refine_dir)
        
        T = self.phase_config['rfdiffusion']['refinement_T']
        max_iterations = self.phase_config['rfdiffusion']['max_refinement_iterations']
        target_pdb = Path(state.target.target_pdb_path)
        target_chain = state.target.chain_id
        
        refined = []
        
        for i, backbone in enumerate(backbones):
            logger.info(f"Refining backbone {i+1}/{len(backbones)}: {backbone.name}")
            
            # Merge target and binder for refinement input
            merge_dir = refine_dir / f"backbone_{i:03d}_merged"
            ensure_dir(merge_dir)
            merged_pdb = merge_dir / "complex.pdb"
            
            try:
                self.rfdiffusion._merge_target_binder(
                    target_pdb=target_pdb,
                    binder_pdb=backbone,
                    output_pdb=merged_pdb,
                    target_chain=target_chain
                )
                
                # Renumber residues starting from 0 (required for partial diffusion)
                renumbered_pdb = merge_dir / "complex_renumbered.pdb"
                self.rfdiffusion._renumber_pdb(
                    input_pdb=merged_pdb,
                    output_pdb=renumbered_pdb,
                    start_from=0
                )
                current_backbone = renumbered_pdb
                
            except Exception as e:
                logger.error(f"Failed to merge/renumber target and binder: {str(e)}")
                refined.append(backbone)
                continue
            
            for iteration in range(max_iterations):
                try:
                    iter_dir = refine_dir / f"backbone_{i:03d}_iter_{iteration}"
                    ensure_dir(iter_dir)
                    
                    refined_backbone = self.rfdiffusion.refine(
                        input_pdb=current_backbone,
                        output_dir=iter_dir,
                        T=T,
                        target_chain=target_chain,
                        binder_chain='B'
                    )
                    
                    current_backbone = refined_backbone
                    
                except Exception as e:
                    logger.warning(f"Refinement iteration {iteration} failed: {str(e)}")
                    break
            
            # Extract binder chain only for ProteinMPNN
            # (Refinement output contains both target and binder)
            extract_dir = refine_dir / f"backbone_{i:03d}_binder_only"
            ensure_dir(extract_dir)
            binder_only_pdb = extract_dir / "binder.pdb"
            
            try:
                self.rfdiffusion._extract_chain_from_pdb(
                    input_pdb=current_backbone,
                    output_pdb=binder_only_pdb,
                    chain_id='B'
                )
                refined.append(binder_only_pdb)
                logger.info(f"  Extracted binder chain: {binder_only_pdb}")
            except Exception as e:
                logger.error(f"Failed to extract binder chain: {str(e)}")
                refined.append(backbone)  # Fallback to original
        
        return refined
    
    def _design_sequences(self, backbones: List[Path], tool_out_dir: Path,
                         state: PipelineState, candidates_dir: Path) -> List[DesignCandidate]:
        """Design sequences with ProteinMPNN"""
        mpnn_dir = tool_out_dir / "mpnn"
        ensure_dir(mpnn_dir)
        
        num_seq_per_target = self.phase_config['proteinmpnn']['num_seq_per_target']
        temps = self.phase_config['proteinmpnn']['sampling_temps']
        batch_size = self.phase_config['proteinmpnn'].get('batch_size', 1)
        seed = self.phase_config['proteinmpnn'].get('seed', 37)
        design_chains = self.phase_config['proteinmpnn'].get('design_chains', 'B')
        fixed_positions_jsonl = self.phase_config['proteinmpnn'].get('fixed_positions_jsonl', '')
        
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
                    temps=temps,
                    batch_size=batch_size,
                    seed=seed,
                    design_chains=design_chains,
                    fixed_positions_jsonl=(Path(fixed_positions_jsonl) if fixed_positions_jsonl else None)
                )
                
                # Create candidate for each sequence
                for j, (sequence, source_fasta) in enumerate(sequences):
                    candidate_id = get_next_candidate_id(state)
                    
                    candidate = DesignCandidate(
                        candidate_id=candidate_id,
                        parent_id=None,
                        binder_sequence=sequence,
                        binder_pdb_path=str(backbone),
                        binder_fasta_path=str(source_fasta),
                        stage="generated",
                        lineage=[f"denovo_backbone_{i}", f"mpnn_seq_{j}"]
                    )
                    
                    # Save candidate
                    candidate.save(candidates_dir)
                    candidates.append(candidate)
                    # IMPORTANT: Also add to state so next ID is unique
                    state.candidates.append(candidate)
                    
            except Exception as e:
                logger.error(f"ProteinMPNN failed for backbone {i}: {str(e)}")
                continue
        
        return candidates

