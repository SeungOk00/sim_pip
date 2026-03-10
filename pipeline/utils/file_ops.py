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


def get_run_id() -> str:
    """Generate run ID with timestamp"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")
