"""
Phase 1: Human-in-the-Loop Target Discovery
"""
from pathlib import Path
from typing import List, Optional
import logging 
from datetime import datetime
from ..models import TargetSpec, PipelineState
from ..utils.validation import validate_pdb_file, validate_hotspot_residues

logger = logging.getLogger(__name__)


class Phase1TargetDiscovery:
    """Phase 1: Target specification with human approval"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def run(self, state: PipelineState,
            target_pdb_path: str,
            chain_id: str,
            hotspot_residues: List[int],
            pocket_definition: dict = None,
            notes: str = "") -> PipelineState:
        """
        Run Phase 1: Create and validate target specification
        
        Args:
            state: Current pipeline state
            target_pdb_path: Path to target PDB file
            chain_id: Target chain identifier
            hotspot_residues: List of hotspot residue numbers (approved by researcher)
            pocket_definition: Optional pocket definition (residue list or coordinate box)
            notes: Optional notes/comments
        
        Returns:
            Updated pipeline state
        """
        logger.info("=" * 80)
        logger.info("PHASE 1: Target Discovery")
        logger.info("=" * 80)
        
        target_pdb = Path(target_pdb_path)
        
        # Validation
        if not validate_pdb_file(target_pdb):
            raise ValueError(f"Invalid target PDB file: {target_pdb_path}")
        
        if not validate_hotspot_residues(hotspot_residues, target_pdb):
            raise ValueError(f"Invalid hotspot residues: {hotspot_residues}")
        
        # Generate target ID
        target_id = f"T{state.run_id.replace('-', '').replace('_', '')[:10]}"
        now = datetime.now()
        date_dir = now.strftime("%Y-%m-%d")
        time_dir = now.strftime("%H-%M-%S")

        project_root = Path(self.config['project_root'])

        # Normalize initial input under inputs/pdb/YYYY-MM-DD/HH-MM-SS/
        inputs_pdb_dir = project_root / self.config['paths']['inputs_pdb'] / date_dir / time_dir
        inputs_pdb_dir.mkdir(parents=True, exist_ok=True)
        normalized_target_pdb = inputs_pdb_dir / target_pdb.name
        import shutil
        shutil.copy2(target_pdb, normalized_target_pdb)

        # Create target metadata directory
        target_dir = project_root / self.config['paths']['targets'] / target_id
        target_dir.mkdir(parents=True, exist_ok=True)

        # Default pocket definition
        if pocket_definition is None:
            pocket_definition = {
                "type": "residue_list",
                "residues": hotspot_residues
            }
        
        # Create TargetSpec
        target_spec = TargetSpec(
            target_id=target_id,
            target_pdb_path=str(normalized_target_pdb),
            chain_id=chain_id,
            pocket_definition=pocket_definition,
            hotspot_residues=hotspot_residues,
            notes=notes
        )
        
        # Save target spec
        target_spec.save(target_dir / "hotspot.json")
        
        # Update state
        state.target = target_spec
        state.current_phase = "phase2"

        logger.info(f"Target ID: {target_id}")
        logger.info(f"Target PDB: {normalized_target_pdb}")
        logger.info(f"Chain: {chain_id}")
        logger.info(f"Hotspot residues: {hotspot_residues}")
        logger.info(f"Target spec saved to: {target_dir / 'hotspot.json'}")
        logger.info("")
        
        return state
    
    def interactive_approval(self, target_pdb_path: str, 
                           suggested_hotspots: List[int] = None) -> dict:
        """
        Interactive mode for researcher approval
        
        Args:
            target_pdb_path: Path to target PDB
            suggested_hotspots: Optional RAG-suggested hotspots
        
        Returns:
            Dictionary with approved parameters
        """
        print("\n" + "=" * 80)
        print("PHASE 1: Target Discovery - Interactive Mode")
        print("=" * 80)
        print(f"\nTarget PDB: {target_pdb_path}")
        
        if suggested_hotspots:
            print(f"\nSuggested hotspot residues: {suggested_hotspots}")
        
        # Get chain ID
        chain_id = input("\nEnter target chain ID (e.g., A): ").strip()
        
        # Get hotspot residues
        print("\nEnter hotspot residue numbers (comma-separated, e.g., 23,45,67,89):")
        hotspot_input = input("> ").strip()
        hotspot_residues = [int(x.strip()) for x in hotspot_input.split(',')]
        
        # Get notes
        notes = input("\nEnter any notes/comments (optional): ").strip()
        
        # Confirmation
        print("\n" + "-" * 80)
        print("Review your inputs:")
        print(f"  Chain ID: {chain_id}")
        print(f"  Hotspot residues: {hotspot_residues}")
        print(f"  Notes: {notes if notes else '(none)'}")
        print("-" * 80)
        
        confirm = input("\nConfirm and proceed? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            raise ValueError("Target specification not approved")
        
        return {
            "chain_id": chain_id,
            "hotspot_residues": hotspot_residues,
            "notes": notes
        }
