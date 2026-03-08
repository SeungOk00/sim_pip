"""
Configuration management
"""
import yaml
from pathlib import Path
from typing import Dict, Any


DEFAULT_CONFIG = {
    "project_root": "/home01/hpc194a02/test/sim_pip",
    
    # Paths
    "paths": {
        "inputs_pdb": "inputs/pdb",
        "inputs_fasta": "inputs/fasta",
        "outputs": "outputs",
        "targets": "targets",
        "runs": "runs",
        "candidates": "candidates",
        "configs": "configs"
    },
    
    # Phase 2: Generation
    "phase2": {
        "rfdiffusion": {
            "path": "/home01/hpc194a02/test/sim_pip/rfdiffusion",
            "de_novo_T": 50,
            "refinement_T": 15,
            "num_designs": 2,
            "target_residues": "982-999",
            "binder_length": "80-80",
            "noise_scale": 0.0,
            "output_prefix": "binder",
            "max_refinement_iterations": 3
        },
        "proteinmpnn": {
            "path": "/home01/hpc194a02/test/sim_pip/proteinmpnn",
            "num_seq_per_target": 8,
            "sampling_temps": [0.1, 0.2],
            "batch_size": 1,
            "seed": 37,
            "design_chains": "B",
            "fixed_positions_jsonl": ""
        },
        "max_candidates_per_target": 100
    },
    # Phase 3-A: Fast Screening
    "phase3_fast": {
        "chai": {
            "path": "",
            "command_template": "python -m chai_lab.run --target {target_pdb} --binder {binder_fasta} --output_dir {output_dir}",
            "output_file": "predicted_complex.pdb"
        },
        "boltz": {
            "enabled": True,
            "path": "",
            "command_template": "boltz predict --target {target_pdb} --binder {binder_fasta} --output_dir {output_dir}",
            "output_file": "predicted_complex.pdb"
        },
        "gates": {
            "consensus_pass_dockq": 0.49,
            "consensus_refine_dockq": 0.23,
            "single_model_pass_conf": 0.7,
            "single_model_refine_conf": 0.5
        }
    },
    
    # Phase 3-B: Deep Validation
    "phase3_deep": {
        "colabfold": {
            "path": "/home01/hpc194a02/test/sim_pip/ColabFold"
        },
        "gates": {
            "rmsd_consensus_threshold": 2.0,
            "pae_interaction_threshold": 5.0
        }
    },
    
    # Phase 4: Optimization
    "phase4": {
        "rosetta": {
            "enabled": True,
            "fastrelax_cycles": 5
        },
        "objectives": {
            "interface_ddg_target": -30.0,
            "sap_target": 40.0,
            "total_score_per_res_target": -3.0
        },
        "constraints": {
            "packstat_min": 0.60,
            "overall_rmsd_max": 2.0,
            "epitope_rmsd_max": 1.0,
            "rg_max": 16.0,
            "mhc2_strong_binders_max": 0
        },
        "nsga2": {
            "population_size": 100,
            "generations": 50
        },
        "final_selection": 96
    },
    
    # Phase 5: Lab Automation
    "phase5": {
        "sop_template": "configs/sop_template.md",
        "neo4j": {
            "enabled": False,
            "uri": "bolt://localhost:7687"
        }
    },
    
    # Execution
    "execution": {
        "dry_run": False,
        "retry_count": 2,
        "parallel_jobs": 4
    }
}


class Config:
    """Configuration manager"""
    
    def __init__(self, config_path: str = None):
        self.config = DEFAULT_CONFIG.copy()
        if config_path and Path(config_path).exists():
            self.load(config_path)
    
    def load(self, config_path: str):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f)
        self._merge_config(self.config, user_config)
    
    def _merge_config(self, base: Dict, update: Dict):
        """Recursively merge configurations"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def save(self, config_path: str):
        """Save configuration to YAML file"""
        with open(config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
    
    def get(self, key_path: str, default=None) -> Any:
        """Get config value by dot-separated path"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value: Any):
        """Set config value by dot-separated path"""
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def to_dict(self) -> Dict:
        """Get full configuration as dictionary"""
        return self.config.copy()


