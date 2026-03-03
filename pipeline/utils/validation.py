"""
Validation utilities
"""
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def validate_pdb_file(pdb_path: Path) -> bool:
    """Validate PDB file format"""
    if not pdb_path.exists():
        logger.error(f"PDB file not found: {pdb_path}")
        return False
    
    with open(pdb_path) as f:
        lines = f.readlines()
    
    # Check for ATOM records
    atom_lines = [l for l in lines if l.startswith('ATOM')]
    if not atom_lines:
        logger.error(f"No ATOM records found in {pdb_path}")
        return False
    
    return True


def validate_fasta_file(fasta_path: Path) -> bool:
    """Validate FASTA file format"""
    if not fasta_path.exists():
        logger.error(f"FASTA file not found: {fasta_path}")
        return False
    
    with open(fasta_path) as f:
        lines = f.readlines()
    
    if not lines or not lines[0].startswith('>'):
        logger.error(f"Invalid FASTA format in {fasta_path}")
        return False
    
    return True


def validate_hotspot_residues(hotspot_residues: List[int], pdb_path: Path) -> bool:
    """Validate hotspot residues exist in PDB"""
    # Simple validation - check residues are positive
    if not hotspot_residues:
        logger.warning("No hotspot residues provided")
        return False
    
    if any(r <= 0 for r in hotspot_residues):
        logger.error("Invalid hotspot residue numbers (must be > 0)")
        return False
    
    return True


def validate_sequence(sequence: str) -> bool:
    """Validate protein sequence"""
    valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
    sequence = sequence.upper().strip()
    
    if not sequence:
        logger.error("Empty sequence")
        return False
    
    invalid_chars = set(sequence) - valid_aa
    if invalid_chars:
        logger.error(f"Invalid amino acids in sequence: {invalid_chars}")
        return False
    
    return True


def validate_metrics(metrics: Dict[str, float], required_keys: List[str]) -> bool:
    """Validate metrics dictionary has required keys"""
    missing_keys = set(required_keys) - set(metrics.keys())
    if missing_keys:
        logger.warning(f"Missing metrics: {missing_keys}")
        return False
    return True
