"""
Tool wrapper utilities
"""
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ToolRunner:
    """Base class for running external tools"""
    
    def __init__(self, tool_name: str, tool_path: str, dry_run: bool = False):
        self.tool_name = tool_name
        self.tool_path = Path(tool_path)
        self.dry_run = dry_run
    
    def run(self, command: List[str], cwd: Optional[Path] = None, 
            retry_count: int = 2) -> Tuple[int, str, str]:
        """
        Run command with retry logic
        
        Returns:
            (exit_code, stdout, stderr)
        """
        cmd_str = " ".join(str(c) for c in command)
        logger.info(f"Running: {cmd_str}")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would execute command")
            return 0, "", ""
        
        for attempt in range(retry_count + 1):
            try:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1 hour timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"Command succeeded on attempt {attempt + 1}")
                    return result.returncode, result.stdout, result.stderr
                else:
                    logger.warning(f"Command failed on attempt {attempt + 1}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Command timed out on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Command error on attempt {attempt + 1}: {str(e)}")
            
            if attempt < retry_count:
                logger.info(f"Retrying... ({attempt + 1}/{retry_count})")
        
        return -1, "", "Failed after retries"
    
    def get_version(self) -> str:
        """Get tool version"""
        return "unknown"


class RFdiffusionRunner(ToolRunner):
    """RFdiffusion tool wrapper"""
    
    def __init__(self, tool_path: str, dry_run: bool = False):
        super().__init__("RFdiffusion", tool_path, dry_run)
    
    def generate_binder(self, target_pdb: Path, target_chain: str,
                       target_residues: Optional[str], hotspot_residues: List[int],
                       binder_length: Optional[str], output_dir: Path, 
                       num_designs: int = 2, T: int = 50,
                       noise_scale: float = 0.0,
                       output_prefix: str = "binder") -> List[Path]:
        """
        Run de novo binder generation
        
        Args:
            target_pdb: Path to target PDB file
            target_chain: Target chain ID (e.g., 'A')
            target_residues: Target residues (e.g., '1-150')
            hotspot_residues: List of hotspot residue numbers
            binder_length: Binder length range (e.g., '70-100')
            output_dir: Output directory
            num_designs: Number of designs to generate
            T: Number of diffusion steps
            noise_scale: Noise scale (0-1, lower = better quality but less diversity)
        
        Returns:
            List of generated PDB files
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Format optional fields only when provided.
        hotspot_str = ",".join([f"{target_chain}{r}" for r in hotspot_residues]) if hotspot_residues else ""
        
        command = [
            "python",
            str(self.tool_path / "scripts/run_inference.py"),
            f"inference.input_pdb={target_pdb}",
            f"inference.output_prefix={output_dir}/{output_prefix}",
            f"inference.num_designs={num_designs}",
            f"diffuser.T={T}",
            f"denoiser.noise_scale_ca={noise_scale}",
            f"denoiser.noise_scale_frame={noise_scale}"
        ]
        if target_residues and binder_length:
            contig_str = f"{target_chain}{target_residues}/0 {binder_length}"
            command.append(f"contigmap.contigs=[{contig_str}]")
        if hotspot_str:
            command.append(f"ppi.hotspot_res=[{hotspot_str}]")
        
        # Remove quotes for actual execution (shell handles them)
        command_str = " ".join(command)
        
        logger.info(f"RFdiffusion command: {command_str}")
        
        exit_code, stdout, stderr = self.run(command, cwd=self.tool_path)
        
        if exit_code != 0:
            raise RuntimeError(f"RFdiffusion failed: {stderr}")
        
        # Find generated PDB files (pattern: binder_0.pdb, binder_1.pdb, ...)
        output_files = sorted(output_dir.glob(f"{output_prefix}_*.pdb"))
        return output_files
    
    def generate_denovo(self, target_pdb: Path, hotspot_residues: List[int],
                       output_dir: Path, num_designs: int = 2, 
                       T: int = 50) -> List[Path]:
        """
        Legacy method - wrapper around generate_binder
        Assumes target is chain A, residues 1-150, binder length 70-100
        """
        logger.warning("Using legacy generate_denovo method. Consider using generate_binder instead.")
        return self.generate_binder(
            target_pdb=target_pdb,
            target_chain='A',
            target_residues='1-150',
            hotspot_residues=hotspot_residues,
            binder_length='80-80',
            output_dir=output_dir,
            num_designs=num_designs,
            T=T,
            noise_scale=0.0,
            output_prefix="binder"
        )
    
    def refine(self, input_pdb: Path, output_dir: Path, T: int = 15) -> Path:
        """
        Run partial diffusion for refinement
        
        Note: Partial diffusion requires contig length to match input structure
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate input length (simplified - actual implementation needs PDB parsing)
        # For now, use a placeholder
        logger.warning("Refinement not fully implemented - requires structure length calculation")
        
        command = [
            "python",
            str(self.tool_path / "scripts/run_inference.py"),
            f"inference.input_pdb={input_pdb}",
            f"inference.output_prefix={output_dir}/refined",
            f"inference.num_designs=1",
            f"diffuser.partial_T={T}",
            f"diffuser.T=50"
        ]
        
        exit_code, stdout, stderr = self.run(command, cwd=self.tool_path)
        
        if exit_code != 0:
            raise RuntimeError(f"RFdiffusion refinement failed: {stderr}")
        
        output_file = output_dir / "refined_0.pdb"
        return output_file


class ProteinMPNNRunner(ToolRunner):
    """ProteinMPNN tool wrapper"""

    def __init__(self, tool_path: str, dry_run: bool = False):
        super().__init__("ProteinMPNN", tool_path, dry_run)

    def design_sequence(
        self,
        backbone_pdb: Path,
        output_dir: Path,
        num_seqs: int = 8,
        temps: List[float] = [0.1, 0.2],
        batch_size: int = 1,
        seed: int = 37,
        design_chains: str = "B",
        fixed_positions_jsonl: Optional[Path] = None,
    ) -> List[str]:
        """Design sequences for backbone using parsed jsonl inputs."""
        import json
        import shutil

        output_dir.mkdir(parents=True, exist_ok=True)

        # Prepare a single-PDB input directory for helper scripts.
        input_dir = output_dir / "input_pdb"
        input_dir.mkdir(parents=True, exist_ok=True)
        input_pdb = input_dir / backbone_pdb.name
        if input_pdb.resolve() != backbone_pdb.resolve():
            shutil.copy2(backbone_pdb, input_pdb)

        parsed_jsonl = output_dir / "parsed_pdbs.jsonl"
        assigned_jsonl = output_dir / "assigned_pdbs.jsonl"
        default_fixed_jsonl = output_dir / "fixed_positions.jsonl"

        parse_cmd = [
            "python",
            str(self.tool_path / "helper_scripts/parse_multiple_chains.py"),
            f"--input_path={input_dir}",
            f"--output_path={parsed_jsonl}",
        ]
        exit_code, _, stderr = self.run(parse_cmd, cwd=self.tool_path)
        if exit_code != 0:
            raise RuntimeError(f"ProteinMPNN parse_multiple_chains failed: {stderr}")

        assign_cmd = [
            "python",
            str(self.tool_path / "helper_scripts/assign_fixed_chains.py"),
            f"--input_path={parsed_jsonl}",
            f"--output_path={assigned_jsonl}",
            f"--chain_list={design_chains}",
        ]
        exit_code, _, stderr = self.run(assign_cmd, cwd=self.tool_path)
        if exit_code != 0:
            raise RuntimeError(f"ProteinMPNN assign_fixed_chains failed: {stderr}")

        fixed_jsonl_path = Path(fixed_positions_jsonl) if fixed_positions_jsonl else default_fixed_jsonl
        if not fixed_jsonl_path.exists():
            with open(parsed_jsonl, "r") as f:
                records = [json.loads(line) for line in f if line.strip()]
            fixed_dict: Dict[str, Dict[str, List[int]]] = {}
            for rec in records:
                all_chain_list = [k[-1:] for k in rec.keys() if k.startswith("seq_chain")]
                fixed_dict[rec["name"]] = {chain: [] for chain in all_chain_list}
            with open(fixed_jsonl_path, "w") as f:
                f.write(json.dumps(fixed_dict) + "\n")

        temp_str = " ".join(str(t) for t in temps)
        command = [
            "python",
            str(self.tool_path / "protein_mpnn_run.py"),
            f"--jsonl_path={parsed_jsonl}",
            f"--chain_id_jsonl={assigned_jsonl}",
            f"--fixed_positions_jsonl={fixed_jsonl_path}",
            f"--out_folder={output_dir}",
            f"--num_seq_per_target={num_seqs}",
            f"--sampling_temp={temp_str}",
            f"--seed={seed}",
            f"--batch_size={batch_size}",
        ]

        exit_code, stdout, stderr = self.run(command, cwd=self.tool_path)

        if exit_code != 0:
            raise RuntimeError(f"ProteinMPNN failed: {stderr}")

        # Parse sequences from output.
        sequences = self._parse_mpnn_output(output_dir)
        return sequences

    def _parse_mpnn_output(self, output_dir: Path) -> List[str]:
        """Parse ProteinMPNN output FASTA files."""
        sequences = []
        seq_dir = output_dir / "seqs"
        fasta_files = list(seq_dir.glob("*.fa")) if seq_dir.exists() else list(output_dir.glob("*.fa"))

        for fasta_file in fasta_files:
            with open(fasta_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(">"):
                        sequences.append(line)

        return sequences

class ChaiRunner(ToolRunner):
    """Chai-1 tool wrapper"""
    
    def __init__(self, tool_path: str, dry_run: bool = False):
        super().__init__("Chai-1", tool_path, dry_run)
    
    def predict_complex(self, target_pdb: Path, binder_fasta: Path,
                       output_dir: Path) -> Tuple[Path, Dict[str, float]]:
        """Predict complex structure"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        command = [
            "python",
            str(self.tool_path / "chai_lab/run.py"),
            f"--target={target_pdb}",
            f"--binder={binder_fasta}",
            f"--output_dir={output_dir}"
        ]
        
        exit_code, stdout, stderr = self.run(command, cwd=self.tool_path)
        
        if exit_code != 0:
            raise RuntimeError(f"Chai-1 failed: {stderr}")
        
        # Find output files
        complex_pdb = output_dir / "predicted_complex.pdb"
        confidence_metrics = self._parse_confidence(output_dir)
        
        return complex_pdb, confidence_metrics
    
    def _parse_confidence(self, output_dir: Path) -> Dict[str, float]:
        """Parse confidence metrics from Chai output"""
        # Placeholder - actual implementation depends on Chai output format
        return {"chai_confidence": 0.8}

