"""
File operations utilities
"""
import shutil
from pathlib import Path
from typing import Optional
import hashlib


def ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_file(src: Path, dst: Path) -> Path:
    """Copy file and return destination path"""
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return dst


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_next_candidate_id(state: 'PipelineState') -> str:
    """
    Generate next candidate ID (C000001, C000002, ...) for current run.
    Uses state.candidates list instead of file system to avoid cross-run conflicts.
    """
    if not state.candidates:
        return "C000001"
    
    # Get max candidate number from current state
    existing_nums = []
    for candidate in state.candidates:
        if candidate.candidate_id.startswith('C'):
            try:
                num = int(candidate.candidate_id[1:])
                existing_nums.append(num)
            except ValueError:
                continue
    
    if not existing_nums:
        return "C000001"
    
    max_num = max(existing_nums)
    return f"C{max_num + 1:06d}"


def get_run_id(outputs_root: Optional[Path] = None) -> str:
    """
    Generate sequential run ID for today's date (run_001, run_002, ...)
    
    Args:
        outputs_root: Optional path to outputs directory to check existing runs
        
    Returns:
        Sequential run ID like "run_001", "run_002", etc.
    """
    from datetime import datetime
    
    # If no outputs_root provided, just return run_001
    if outputs_root is None:
        return "run_001"
    
    # Get today's date directory
    date_dir = datetime.now().strftime("%Y-%m-%d")
    
    # Find all existing run directories for today
    existing_runs = []
    
    # Check multiple tool directories for existing runs
    tool_dirs = [
        "rfdiffusion", "proteinmpnn", "phase3_fast", "colabfold", 
        "chai1", "boltz", "rosetta", "lab"
    ]
    
    for tool in tool_dirs:
        tool_path = outputs_root / tool / date_dir
        if tool_path.exists():
            for item in tool_path.iterdir():
                if item.is_dir() and item.name.startswith("run_"):
                    try:
                        num = int(item.name.split("_")[1])
                        existing_runs.append(num)
                    except (ValueError, IndexError):
                        continue
    
    # Get next run number
    if not existing_runs:
        return "run_001"
    
    max_run = max(existing_runs)
    return f"run_{max_run + 1:03d}"


def get_date_dir() -> str:
    """Get current date directory (YYYY-MM-DD)"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")
