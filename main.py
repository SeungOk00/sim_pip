"""
Main pipeline execution script
"""
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

from pipeline.config import Config
from pipeline.models import PipelineState
from pipeline.phases.phase1_target import Phase1TargetDiscovery
from pipeline.phases.phase2_generate import Phase2GenerativeDesign
from pipeline.phases.phase3_screen import Phase3ScreeningAndValidation
from pipeline.phases.phase4_optimize import Phase4Optimization
from pipeline.phases.phase5_lab import Phase5LabAutomation
from pipeline.utils.file_ops import ensure_dir, get_run_id


def setup_logging(log_level: str = "INFO", log_file: Path = None):
    """Setup logging configuration"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    # Create formatters and handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    
    handlers = [console_handler]
    
    # File handler (if log file specified)
    if log_file:
        ensure_dir(log_file.parent)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers
    )


def run_pipeline(config: Config, args):
    """Execute the complete pipeline"""
    
    # Initialize state
    run_id = get_run_id()
    state = PipelineState(run_id=run_id, config=config.to_dict())
    
    # Setup run directory
    project_root = Path(config.get('project_root'))
    run_dir = project_root / config.get('paths.runs') / run_id
    ensure_dir(run_dir)
    
    # Save state file path
    state_file = run_dir / "pipeline_state.json"
    
    # Setup logging
    log_file = run_dir / "pipeline.log"
    setup_logging(args.log_level, log_file)
    
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info("PROTEIN BINDER DESIGN PIPELINE")
    logger.info("="*80)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Run Directory: {run_dir}")
    logger.info(f"Log File: {log_file}")
    logger.info("="*80 + "\n")
    
    try:
        # Determine starting phase
        start_phase = args.start_phase if hasattr(args, 'start_phase') else 1
        
        # Phase 1: Target Discovery
        if start_phase <= 1:
            phase1 = Phase1TargetDiscovery(config.to_dict())
            
            if args.interactive:
                # Interactive mode
                approval = phase1.interactive_approval(
                    target_pdb_path=args.target_pdb
                )
                state = phase1.run(
                    state=state,
                    target_pdb_path=args.target_pdb,
                    chain_id=approval['chain_id'],
                    hotspot_residues=approval['hotspot_residues'],
                    notes=approval['notes']
                )
            else:
                # Non-interactive mode (requires all parameters)
                if not args.chain_id or not args.hotspots:
                    raise ValueError("Non-interactive mode requires --chain-id and --hotspots")
                
                hotspot_residues = [int(x.strip()) for x in args.hotspots.split(',')]
                state = phase1.run(
                    state=state,
                    target_pdb_path=args.target_pdb,
                    chain_id=args.chain_id,
                    hotspot_residues=hotspot_residues,
                    notes=args.notes if hasattr(args, 'notes') else ""
                )
            
            state.save(state_file)
        
        # Phase 2: Generative Design
        if start_phase <= 2:
            phase2 = Phase2GenerativeDesign(config.to_dict())
            state = phase2.run(state)
            state.save(state_file)
        
        # Phase 3: Screening and Validation
        if start_phase <= 3:
            phase3 = Phase3ScreeningAndValidation(config.to_dict())
            state = phase3.run(state)
            state.save(state_file)
        
        # Phase 4: Optimization
        if start_phase <= 4:
            phase4 = Phase4Optimization(config.to_dict())
            state = phase4.run(state)
            state.save(state_file)
        
        # Phase 5: Lab Automation
        if start_phase <= 5:
            phase5 = Phase5LabAutomation(config.to_dict())
            state = phase5.run(state)
            state.save(state_file)
        
        logger.info("\n" + "="*80)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info(f"Run ID: {run_id}")
        logger.info(f"State file: {state_file}")
        logger.info(f"Results directory: {run_dir}")
        logger.info("="*80 + "\n")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n\nPipeline interrupted by user!")
        state.save(state_file)
        logger.info(f"State saved to: {state_file}")
        logger.info("You can resume by loading this state file")
        return 130
        
    except Exception as e:
        logger.error(f"\n\nPipeline failed with error: {str(e)}", exc_info=True)
        state.save(state_file)
        logger.info(f"State saved to: {state_file}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Protein Binder Design Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended for first run)
  python main.py --target-pdb target.pdb --interactive
  
  # Non-interactive mode
  python main.py --target-pdb target.pdb --chain-id A --hotspots "23,45,67,89"
  
  # Resume from saved state
  python main.py --resume runs/2026-03-03_001/pipeline_state.json
  
  # Dry run (show commands without executing)
  python main.py --target-pdb target.pdb --chain-id A --hotspots "23,45,67" --dry-run
        """
    )
    
    # Input arguments
    parser.add_argument('--target-pdb', type=str, 
                       help='Path to target PDB file')
    parser.add_argument('--chain-id', type=str,
                       help='Target chain identifier (e.g., A)')
    parser.add_argument('--hotspots', type=str,
                       help='Comma-separated hotspot residue numbers (e.g., "23,45,67,89")')
    parser.add_argument('--notes', type=str, default="",
                       help='Optional notes/comments')
    
    # Execution mode
    parser.add_argument('--interactive', action='store_true',
                       help='Run in interactive mode with user prompts')
    parser.add_argument('--resume', type=str,
                       help='Resume from saved state file')
    parser.add_argument('--start-phase', type=int, default=1, choices=[1,2,3,4,5],
                       help='Starting phase (default: 1)')
    
    # Configuration
    parser.add_argument('--config', type=str, default='configs/run.yaml',
                       help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show commands without executing')
    
    # Logging
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.resume and not args.target_pdb:
        parser.error("Either --target-pdb or --resume is required")
    
    # Load configuration
    config = Config(args.config if Path(args.config).exists() else None)
    
    # Override dry-run setting
    if args.dry_run:
        config.set('execution.dry_run', True)
    
    # Run pipeline
    exit_code = run_pipeline(config, args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
