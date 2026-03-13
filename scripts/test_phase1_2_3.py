#!/usr/bin/env python3
"""
Test script for Phase 1-2-3 of the binder design pipeline

Usage:
    # Activate virtual environment first
    source .venv/bin/activate          # Linux/macOS
    .venv\\Scripts\\activate           # Windows
    
    # Then run the script from project root
    python scripts/test_phase1_2_3.py
"""
import sys
import os
import logging
from pathlib import Path
# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Check if virtual environment is activated
try:
    import yaml
except ImportError:
    print("\n" + "=" * 80)
    print("ERROR: Required modules not found!")
    print("=" * 80)
    print("\nIt looks like the virtual environment is not activated.")
    print("\nPlease activate the virtual environment first:")
    print("  On Linux/macOS: source .venv/bin/activate")
    print("  On Windows:     .venv\\Scripts\\activate")
    print("\nOr install requirements:")
    print("  pip install -r requirements.txt")
    print("=" * 80 + "\n")
    sys.exit(1)

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
    
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Create pipeline state
    from pipeline.utils.file_ops import get_run_id
    outputs_root = project_root / "data" / "outputs"
    run_id = get_run_id(outputs_root)
    state = PipelineState(run_id=run_id)
    logger.info(f"Created new run: {state.run_id}")
    
    # ==========================================================================
    # PHASE 1: Target Discovery
    # ==========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("TESTING PHASE 1: Target Discovery")
    logger.info("=" * 80)
    
    phase1 = Phase1TargetDiscovery(config.to_dict())
    
    # Test with the target.pdb from inputs directory
    # Note: You need to provide a target PDB file
    target_pdb_path = project_root / "inputs/pdb/target.pdb"
    
    # Ensure directory exists
    target_pdb_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Download target PDB if not exists
    if not target_pdb_path.exists():
        logger.warning(f"Target PDB not found at {target_pdb_path}")
        logger.info("Attempting to download test target (4IBM - Insulin Receptor)...")
        
        try:
            import urllib.request
            pdb_url = "https://files.rcsb.org/download/4IBM.pdb"
            logger.info(f"Downloading from {pdb_url}...")
            urllib.request.urlretrieve(pdb_url, str(target_pdb_path))
            logger.info(f"✓ Downloaded target.pdb successfully to {target_pdb_path}")
        except Exception as e:
            logger.warning(f"Failed to download: {e}")
            logger.info("Trying to use example PDB files from tools/proteinmpnn/inputs/...")
            
            # Try to find any .pdb file in inputs/pdb or use example
            pdb_files = list((project_root / "inputs/pdb").rglob("*.pdb"))
            if pdb_files:
                target_pdb_path = pdb_files[0]
                logger.info(f"Using alternative PDB file: {target_pdb_path}")
            else:
                # Try to copy from example files
                example_pdbs = list((project_root / "tools/proteinmpnn/inputs").rglob("*.pdb"))
                if example_pdbs:
                    import shutil
                    example_pdb = example_pdbs[0]
                    shutil.copy(example_pdb, target_pdb_path)
                    logger.info(f"✓ Copied example PDB: {example_pdb.name}")
                else:
                    logger.error("\n" + "=" * 80)
                    logger.error("ERROR: No PDB file found!")
                    logger.error("=" * 80)
                    logger.error("\nPlease provide a target PDB file:")
                    logger.error(f"  1. Place your PDB file at: inputs/pdb/target.pdb")
                    logger.error(f"  2. Or download manually:")
                    logger.error(f"     wget https://files.rcsb.org/download/4IBM.pdb -O inputs/pdb/target.pdb")
                    logger.error("=" * 80 + "\n")
                    raise FileNotFoundError("No target.pdb found and unable to download")
    
    chain_id = "A"
    hotspot_residues = [982, 990, 995]  # Insulin receptor kinase domain hotspots
    notes = "Test run for insulin receptor kinase domain (4IBM) - Phase 1-2-3 (CPU-friendly)"
    
    # Override config for CPU-friendly test
    logger.info("\n" + "=" * 80)
    logger.info("ADJUSTING CONFIG FOR CPU MODE")
    logger.info("=" * 80)
    logger.info("Reducing num_designs to 1 and using smaller target for CPU compatibility")
    
    # Modify config for CPU mode
    config.config['phase2']['rfdiffusion']['num_designs'] = 1
    config.config['phase2']['rfdiffusion']['target_residues'] = "982-999"  # Smaller range
    config.config['phase2']['rfdiffusion']['binder_length'] = "60-60"      # Fixed small size
    
    logger.info(f"  num_designs: {config.config['phase2']['rfdiffusion']['num_designs']}")
    logger.info(f"  target_residues: {config.config['phase2']['rfdiffusion']['target_residues']}")
    logger.info(f"  binder_length: {config.config['phase2']['rfdiffusion']['binder_length']}")
    
    logger.info(f"\nTest inputs:")
    logger.info(f"  Target PDB: {target_pdb_path}")
    logger.info(f"  Chain ID: {chain_id}")
    logger.info(f"  Hotspot residues: {hotspot_residues}")
    logger.info(f"  Notes: {notes}")
    
    try:
        state = phase1.run(
            state=state,
            target_pdb_path=str(target_pdb_path),
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
