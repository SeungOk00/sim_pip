#!/usr/bin/env python3
"""
Test script for Phase 1-2-3 of the binder design pipeline
"""
import sys
import logging
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.config import Config
from pipeline.models import PipelineState
from pipeline.phases.phase1_target import Phase1TargetDiscovery
from pipeline.phases.phase2_generate import Phase2GenerativeDesign
from pipeline.phases.phase3_screen import Phase3ScreeningAndValidation

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_phase1_2_3():
    """Test Phase 1, Phase 2, and Phase 3"""
    
    # Load configuration
    logger.info("Loading configuration...")
    config = Config()
    
    # Create pipeline state
    from datetime import datetime
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    state = PipelineState(run_id=run_id)
    logger.info(f"Created new run: {state.run_id}")
    
    # ==========================================================================
    # PHASE 1: Target Discovery
    # ==========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("TESTING PHASE 1: Target Discovery")
    logger.info("=" * 80)
    
    phase1 = Phase1TargetDiscovery(config.to_dict())
    
    # Test with the target.pdb we used for RFdiffusion
    target_pdb_path = "/home01/hpc194a02/test/sim_pip/test_rfdiffusion/target.pdb"
    chain_id = "A"
    hotspot_residues = [982, 990, 995]  # Same as we used before
    notes = "Test run for insulin receptor kinase domain (4IBM) - Phase 1-2-3"
    
    logger.info(f"\nTest inputs:")
    logger.info(f"  Target PDB: {target_pdb_path}")
    logger.info(f"  Chain ID: {chain_id}")
    logger.info(f"  Hotspot residues: {hotspot_residues}")
    logger.info(f"  Notes: {notes}")
    
    try:
        state = phase1.run(
            state=state,
            target_pdb_path=target_pdb_path,
            chain_id=chain_id,
            hotspot_residues=hotspot_residues,
            notes=notes
        )
        logger.info("✓ Phase 1 completed successfully")
    except Exception as e:
        logger.error(f"✗ Phase 1 failed: {e}")
        raise
    
    # ==========================================================================
    # PHASE 2: Generative Design
    # ==========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("TESTING PHASE 2: Generative Design")
    logger.info("=" * 80)
    
    phase2 = Phase2GenerativeDesign(config.to_dict())
    
    try:
        state = phase2.run(state)
        logger.info("✓ Phase 2 completed successfully")
    except Exception as e:
        logger.error(f"✗ Phase 2 failed: {e}")
        raise
    
    # ==========================================================================
    # PHASE 3: Screening and Validation
    # ==========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("TESTING PHASE 3: Screening and Validation")
    logger.info("=" * 80)
    
    phase3 = Phase3ScreeningAndValidation(config.to_dict())
    
    try:
        state = phase3.run(state)
        logger.info("✓ Phase 3 completed successfully")
    except Exception as e:
        logger.error(f"✗ Phase 3 failed: {e}")
        raise
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Run ID: {state.run_id}")
    logger.info(f"Target ID: {state.target.target_id}")
    logger.info(f"Current Phase: {state.current_phase}")
    logger.info(f"Total Candidates: {len(state.candidates)}")
    logger.info(f"Run Records: {len(state.run_records)}")
    
    # Candidate breakdown by stage
    stages = {}
    for candidate in state.candidates:
        stage = candidate.stage
        stages[stage] = stages.get(stage, 0) + 1
    
    logger.info(f"\nCandidate breakdown by stage:")
    for stage, count in stages.items():
        logger.info(f"  {stage}: {count}")
    
    if state.candidates:
        logger.info(f"\nFirst 5 candidates:")
        for i, candidate in enumerate(state.candidates[:5]):
            decision = candidate.decision.get('gate', 'N/A')
            logger.info(f"  {i+1}. {candidate.candidate_id} - {candidate.stage} - {decision}")
    
    # Save state
    project_root = Path(config.get('project_root'))
    run_dir = project_root / config.get('paths.runs') / state.run_id
    state_file = run_dir / "pipeline_state.json"
    state.save(state_file)
    logger.info(f"\nPipeline state saved to: {state_file}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ ALL TESTS PASSED")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_phase1_2_3()
