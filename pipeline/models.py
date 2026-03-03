"""
Data models for the binder design pipeline
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
from datetime import datetime


@dataclass
class TargetSpec:
    """Phase 1 Output: Target specification"""
    target_id: str
    target_pdb_path: str
    chain_id: str
    pocket_definition: Dict[str, Any]  # residue list or coordinate box
    hotspot_residues: List[int]  # Approved by researcher
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def save(self, path: Path):
        """Save target spec to JSON"""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TargetSpec':
        return cls(**data)
    
    @classmethod
    def load(cls, path: Path) -> 'TargetSpec':
        """Load target spec from JSON"""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class DesignCandidate:
    """Common structure for all phases"""
    candidate_id: str
    parent_id: Optional[str] = None
    binder_sequence: str = ""
    binder_pdb_path: str = ""
    complex_pdb_path: str = ""
    stage: str = "generated"  # generated/refined/fast_screened/deep_validated/optimized/selected/failed
    metrics: Dict[str, float] = field(default_factory=dict)
    decision: Dict[str, str] = field(default_factory=dict)
    lineage: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def save(self, base_dir: Path):
        """Save candidate to its directory"""
        cand_dir = base_dir / self.candidate_id
        cand_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        with open(cand_dir / "metadata.json", 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        # Save sequence if available
        if self.binder_sequence:
            with open(cand_dir / "seq.fasta", 'w') as f:
                f.write(f">{self.candidate_id}\n{self.binder_sequence}\n")
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DesignCandidate':
        return cls(**data)
    
    @classmethod
    def load(cls, cand_dir: Path) -> 'DesignCandidate':
        """Load candidate from directory"""
        with open(cand_dir / "metadata.json", 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class RunRecord:
    """Execution log for reproducibility"""
    tool_name: str
    tool_version: str
    command: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    start_time: str
    end_time: str = ""
    exit_code: int = 0
    stderr_tail: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def save(self, path: Path):
        """Append run record to log file"""
        with open(path, 'a') as f:
            f.write(json.dumps(self.to_dict()) + "\n")


@dataclass
class PipelineState:
    """Global pipeline state"""
    run_id: str
    target: Optional[TargetSpec] = None
    candidates: List[DesignCandidate] = field(default_factory=list)
    current_phase: str = "phase1"
    config: Dict[str, Any] = field(default_factory=dict)
    run_records: List[RunRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        data = {
            "run_id": self.run_id,
            "target": self.target.to_dict() if self.target else None,
            "candidates": [c.to_dict() for c in self.candidates],
            "current_phase": self.current_phase,
            "config": self.config,
            "run_records": [r.to_dict() for r in self.run_records]
        }
        return data
    
    def save(self, path: Path):
        """Save pipeline state"""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PipelineState':
        state = cls(run_id=data['run_id'])
        if data.get('target'):
            state.target = TargetSpec.from_dict(data['target'])
        state.candidates = [DesignCandidate.from_dict(c) for c in data.get('candidates', [])]
        state.current_phase = data.get('current_phase', 'phase1')
        state.config = data.get('config', {})
        state.run_records = [RunRecord(**r) for r in data.get('run_records', [])]
        return state
    
    @classmethod
    def load(cls, path: Path) -> 'PipelineState':
        """Load pipeline state"""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_candidates_by_stage(self, stage: str) -> List[DesignCandidate]:
        """Filter candidates by stage"""
        return [c for c in self.candidates if c.stage == stage]
    
    def add_run_record(self, record: RunRecord):
        """Add execution record"""
        self.run_records.append(record)
