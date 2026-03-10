"""
Tool wrapper utilities
"""
import subprocess
import shlex
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
            retry_count: int = 2, env: Optional[Dict] = None) -> Tuple[int, str, str]:
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
        
        # Setup environment
        import os
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        for attempt in range(retry_count + 1):
            try:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=3600,  # 1 hour timeout
                    env=run_env
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
        
        # Add rfdiffusion directory and SE3Transformer to PYTHONPATH for imports
        import os
        se3_path = self.tool_path / "env/SE3Transformer"
        env = {
            'PYTHONPATH': f"{self.tool_path}:{se3_path}:{os.environ.get('PYTHONPATH', '')}"
        }
        
        exit_code, stdout, stderr = self.run(command, cwd=self.tool_path, env=env)
        
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
    
    def _renumber_pdb(self, input_pdb: Path, output_pdb: Path, start_from: int = 0) -> Path:
        """
        Renumber PDB residues to start from a specific number (usually 0 or 1).
        Preserves chain IDs and other information.
        
        Args:
            input_pdb: Input PDB file
            output_pdb: Output PDB file with renumbered residues
            start_from: Starting residue number (default: 0)
        
        Returns:
            Path to renumbered PDB file
        """
        output_pdb.parent.mkdir(parents=True, exist_ok=True)
        
        # Track residue mapping per chain
        chain_residue_map = {}
        
        # First pass: build mapping
        with open(input_pdb, 'r') as f:
            for line in f:
                if not line.startswith(('ATOM', 'HETATM')):
                    continue
                
                chain_id = line[21].strip()
                old_resseq = int(line[22:26].strip())
                icode = line[26].strip()
                
                key = (old_resseq, icode)
                
                if chain_id not in chain_residue_map:
                    chain_residue_map[chain_id] = {}
                
                if key not in chain_residue_map[chain_id]:
                    new_resnum = start_from + len(chain_residue_map[chain_id])
                    chain_residue_map[chain_id][key] = new_resnum
        
        # Second pass: write renumbered PDB
        with open(output_pdb, 'w') as out:
            with open(input_pdb, 'r') as f:
                for line in f:
                    if line.startswith(('ATOM', 'HETATM')):
                        chain_id = line[21].strip()
                        old_resseq = int(line[22:26].strip())
                        icode = line[26].strip()
                        
                        key = (old_resseq, icode)
                        new_resseq = chain_residue_map[chain_id][key]
                        
                        # Replace residue number (columns 23-26) and clear icode (column 27)
                        new_line = line[:22] + f"{new_resseq:4d} " + line[27:]
                        out.write(new_line)
                    elif line.startswith('TER'):
                        # Update TER record residue number
                        if len(line) > 26:
                            chain_id = line[21].strip()
                            try:
                                old_resseq = int(line[22:26].strip())
                                icode = line[26].strip()
                                key = (old_resseq, icode)
                                new_resseq = chain_residue_map.get(chain_id, {}).get(key, old_resseq)
                                new_line = line[:22] + f"{new_resseq:4d} " + line[27:]
                                out.write(new_line)
                            except:
                                out.write(line)
                        else:
                            out.write(line)
                    else:
                        out.write(line)
        
        logger.info(f"Renumbered PDB: {input_pdb.name} -> {output_pdb.name} (starting from {start_from})")
        return output_pdb
    
    def _extract_chain_from_pdb(self, input_pdb: Path, output_pdb: Path, chain_id: str) -> Path:
        """
        Extract a specific chain from PDB file.
        
        Args:
            input_pdb: Input PDB file
            output_pdb: Output PDB file
            chain_id: Chain ID to extract
        
        Returns:
            Path to extracted chain PDB
        """
        output_pdb.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_pdb, 'w') as out:
            with open(input_pdb, 'r') as f:
                for line in f:
                    if line.startswith(('ATOM', 'HETATM')):
                        if line[21].strip() == chain_id:
                            out.write(line)
                    elif line.startswith('TER'):
                        # Write TER only if it's for our chain
                        if len(line) > 21 and line[21].strip() == chain_id:
                            out.write(line)
            out.write('END\n')
        
        return output_pdb
    
    def _merge_target_binder(self, target_pdb: Path, binder_pdb: Path, 
                            output_pdb: Path, target_chain: str = 'A') -> Path:
        """
        Merge target and binder PDB files into a complex.
        
        Args:
            target_pdb: Target PDB file
            binder_pdb: Binder PDB file (chain B)
            output_pdb: Output complex PDB file
            target_chain: Target chain ID (default: A)
        
        Returns:
            Path to merged PDB file
        """
        output_pdb.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_pdb, 'w') as out:
            # Write target chain
            with open(target_pdb, 'r') as f:
                for line in f:
                    if line.startswith(('ATOM', 'HETATM')):
                        # Ensure target uses specified chain
                        new_line = line[:21] + target_chain + line[22:]
                        out.write(new_line)
                    elif line.startswith('TER'):
                        out.write(line)
            
            # Write binder chain (should already be chain B)
            with open(binder_pdb, 'r') as f:
                for line in f:
                    if line.startswith(('ATOM', 'HETATM')):
                        out.write(line)
                    elif line.startswith('TER'):
                        out.write(line)
            
            out.write('END\n')
        
        return output_pdb
    
    def _parse_pdb_chain_info(self, pdb_path: Path) -> Dict[str, Dict]:
        """
        Parse PDB file and return chain information including residue ranges.
        
        Returns:
            Dict mapping chain_id -> {
                'length': int,
                'start': int,
                'end': int
            }
        """
        chain_residues = {}
        
        with open(pdb_path, 'r') as f:
            for line in f:
                if not line.startswith('ATOM'):
                    continue
                if len(line) < 27:
                    continue
                
                chain_id = line[21].strip()
                resseq = int(line[22:26].strip())
                icode = line[26].strip()
                
                key = (chain_id, resseq, icode)
                if chain_id not in chain_residues:
                    chain_residues[chain_id] = set()
                chain_residues[chain_id].add(resseq)
        
        # Calculate length and range for each chain
        chain_info = {}
        for chain, residues in chain_residues.items():
            res_list = sorted(residues)
            chain_info[chain] = {
                'length': len(residues),
                'start': min(res_list),
                'end': max(res_list)
            }
        
        return chain_info
    
    def refine(self, input_pdb: Path, output_dir: Path, T: int = 15, 
               target_chain: str = 'A', binder_chain: str = 'B') -> Path:
        """
        Run partial diffusion for refinement
        
        Args:
            input_pdb: Input PDB file (should be renumbered starting from 0)
            output_dir: Output directory
            T: Number of diffusion timesteps for refinement
            target_chain: Target chain ID (default: A)
            binder_chain: Binder chain ID (default: B)
        
        Returns:
            Path to refined PDB file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse structure information
        chain_info = self._parse_pdb_chain_info(input_pdb)
        
        if target_chain not in chain_info or binder_chain not in chain_info:
            raise ValueError(
                f"Required chains not found. Found: {list(chain_info.keys())}, "
                f"Expected: {target_chain}, {binder_chain}"
            )
        
        target_info = chain_info[target_chain]
        binder_info = chain_info[binder_chain]
        
        logger.info(
            f"Refining structure: "
            f"target={target_info['length']} residues ({target_info['start']}-{target_info['end']}), "
            f"binder={binder_info['length']} residues ({binder_info['start']}-{binder_info['end']})"
        )
        
        # For renumbered PDB (starting from 0), use simple format
        # Format: [A0-N/0 M-M] where N=target_end, M=binder_length
        target_range = f"{target_chain}{target_info['start']}-{target_info['end']}"
        binder_len = binder_info['length']
        contig_str = f"{target_range}/0 {binder_len}-{binder_len}"
        
        command = [
            "python",
            str(self.tool_path / "scripts/run_inference.py"),
            f"inference.input_pdb={input_pdb}",
            f"inference.output_prefix={output_dir}/refined",
            f"inference.num_designs=1",
            f"diffuser.partial_T={T}",
            f"diffuser.T=50",
            f"contigmap.contigs=[{contig_str}]"
        ]
        
        # Add rfdiffusion directory and SE3Transformer to PYTHONPATH for imports
        import os
        se3_path = self.tool_path / "env/SE3Transformer"
        env = {
            'PYTHONPATH': f"{self.tool_path}:{se3_path}:{os.environ.get('PYTHONPATH', '')}"
        }
        
        exit_code, stdout, stderr = self.run(command, cwd=self.tool_path, env=env)
        
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
    ) -> List[Tuple[str, Path]]:
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

    def _parse_mpnn_output(self, output_dir: Path) -> List[Tuple[str, Path]]:
        """Parse ProteinMPNN output FASTA files."""
        sequences: List[Tuple[str, Path]] = []
        seq_dir = output_dir / "seqs"
        fasta_files = list(seq_dir.glob("*.fa")) if seq_dir.exists() else list(output_dir.glob("*.fa"))

        for fasta_file in fasta_files:
            with open(fasta_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(">"):
                        sequences.append((line, fasta_file))

        return sequences

class ChaiRunner(ToolRunner):
    """Chai-1 tool wrapper"""
    
    def __init__(self, tool_path: str, dry_run: bool = False):
        super().__init__("Chai-1", tool_path, dry_run)
    
    def predict_complex(
        self,
        target_pdb: Path,
        binder_fasta: Path,
        output_dir: Path,
        command_template: Optional[str] = None,
        input_path: Optional[Path] = None,
        output_file: str = "predicted_complex.pdb",
    ) -> Tuple[Path, Dict[str, float]]:
        """Predict complex structure"""
        output_dir.mkdir(parents=True, exist_ok=True)
        resolved_input = input_path if input_path is not None else binder_fasta

        commands = []
        if command_template:
            commands.append(shlex.split(command_template.format(
                target_pdb=target_pdb,
                binder_fasta=binder_fasta,
                input_path=resolved_input,
                output_dir=output_dir,
            )))
        # pip/module/common fallbacks
        commands.extend([
            ["chai-lab", "fold", str(resolved_input), str(output_dir)],
            ["python", "-m", "chai_lab.main", "fold", str(resolved_input), str(output_dir)],
        ])

        last_err = ""
        for command in commands:
            exit_code, stdout, stderr = self.run(command, cwd=self.tool_path if str(self.tool_path) else None)
            if exit_code == 0:
                break
            last_err = stderr
        else:
            raise RuntimeError(f"Chai-1 failed: {last_err}")

        # Find output files
        complex_pdb = self._find_prediction_file(output_dir, output_file)
        confidence_metrics = self._parse_confidence(output_dir)
        
        return complex_pdb, confidence_metrics

    def _find_prediction_file(self, output_dir: Path, output_file: str) -> Path:
        if output_file:
            explicit = output_dir / output_file
            if explicit.exists():
                return explicit

        chai_cifs = sorted(output_dir.glob("pred.model_idx_*.cif"))
        if chai_cifs:
            return chai_cifs[0]
        chai_pdbs = sorted(output_dir.glob("*.pdb"))
        if chai_pdbs:
            return chai_pdbs[0]

        any_cif = sorted(output_dir.glob("**/*.cif"))
        if any_cif:
            return any_cif[0]
        any_pdb = sorted(output_dir.glob("**/*.pdb"))
        if any_pdb:
            return any_pdb[0]
        raise RuntimeError(f"Chai output structure not found under {output_dir}")
    
    def _parse_confidence(self, output_dir: Path) -> Dict[str, float]:
        """Parse confidence metrics from Chai output"""
        # Placeholder - actual implementation depends on Chai output format
        return {"chai_confidence": 0.8}


class BoltzRunner(ToolRunner):
    """Boltz tool wrapper"""

    def __init__(self, tool_path: str, venv_path: Optional[str] = None, dry_run: bool = False):
        super().__init__("Boltz", tool_path, dry_run)
        self.venv_path = Path(venv_path) if venv_path else None

    def predict_complex(
        self,
        target_pdb: Path,
        binder_fasta: Path,
        output_dir: Path,
        command_template: str,
        input_path: Optional[Path] = None,
        output_file: str = "predicted_complex.pdb",
    ) -> Tuple[Path, Dict[str, float]]:
        """Predict complex structure with Boltz."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use Boltz venv Python if specified
        if self.venv_path:
            venv_python = self.venv_path / "bin" / "python"
            if not venv_python.exists():
                raise RuntimeError(f"Boltz venv Python not found: {venv_python}")
            # Replace 'boltz' command with venv python + module
            cmd = command_template.format(
                target_pdb=target_pdb,
                binder_fasta=binder_fasta,
                output_dir=output_dir,
                input_path=(input_path if input_path is not None else binder_fasta),
            )
            # Replace 'boltz' with 'python -m boltz.main'
            if cmd.startswith('boltz '):
                cmd = f"{venv_python} -m boltz.main " + cmd[6:]
            command = shlex.split(cmd)
        else:
            cmd = command_template.format(
                target_pdb=target_pdb,
                binder_fasta=binder_fasta,
                output_dir=output_dir,
                input_path=(input_path if input_path is not None else binder_fasta),
            )
            command = shlex.split(cmd)

        exit_code, stdout, stderr = self.run(command, cwd=self.tool_path)
        if exit_code != 0:
            raise RuntimeError(f"Boltz failed: {stderr}")

        complex_pdb = self._find_prediction_file(output_dir, output_file)
        confidence_metrics = self._parse_confidence(output_dir)
        return complex_pdb, confidence_metrics

    def _find_prediction_file(self, output_dir: Path, output_file: str) -> Path:
        """Resolve Boltz output structure file from out_dir."""
        if output_file:
            explicit = output_dir / output_file
            if explicit.exists():
                return explicit

        predictions_dir = output_dir / "predictions"
        if predictions_dir.exists():
            cif_files = sorted(predictions_dir.glob("**/*_model_*.cif"))
            if cif_files:
                return cif_files[0]
            pdb_files = sorted(predictions_dir.glob("**/*.pdb"))
            if pdb_files:
                return pdb_files[0]

        # Final fallback
        any_cif = sorted(output_dir.glob("**/*.cif"))
        if any_cif:
            return any_cif[0]
        any_pdb = sorted(output_dir.glob("**/*.pdb"))
        if any_pdb:
            return any_pdb[0]
        raise RuntimeError(f"Boltz output structure not found under {output_dir}")

    def _parse_confidence(self, output_dir: Path) -> Dict[str, float]:
        """Parse confidence metrics from Boltz output."""
        # Placeholder - actual implementation depends on Boltz output format.
        return {"boltz_confidence": 0.8}

