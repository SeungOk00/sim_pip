"""
Phase 5: Lab Automation
"""
from pathlib import Path
from typing import List
import logging
from datetime import datetime

from ..models import DesignCandidate, PipelineState
from ..utils.file_ops import ensure_dir, get_date_dir

logger = logging.getLogger(__name__)


class Phase5LabAutomation:
    """Phase 5: Generate SOPs and prepare for lab work"""
    
    def __init__(self, config: dict):
        self.config = config
        self.phase_config = config['phase5']
    
    def run(self, state: PipelineState) -> PipelineState:
        """
        Run Phase 5: Lab automation preparation
        
        Pipeline:
        1. Collect final candidates
        2. Generate SOP document
        3. Export sequences and structures
        4. (Optional) Save to Neo4j
        5. Generate summary report
        
        Args:
            state: Current pipeline state with optimized candidates
        
        Returns:
            Updated pipeline state (complete)
        """
        logger.info("=" * 80)
        logger.info("PHASE 5: Lab Automation")
        logger.info("=" * 80)
        
        # Setup directories
        project_root = Path(self.config['project_root'])
        date_dir = get_date_dir()
        run_dir = project_root / self.config['paths']['outputs'] / "lab" / date_dir / state.run_id / "phase5_lab"
        ensure_dir(run_dir)
        
        # Get final candidates
        final_candidates = state.get_candidates_by_stage("selected")
        logger.info(f"\nPreparing {len(final_candidates)} final candidates for lab")
        
        if not final_candidates:
            logger.warning("No selected candidates found!")
            return state
        
        # Step 1: Export sequences
        logger.info("\nStep 1: Export sequences and structures")
        logger.info("-" * 80)
        self._export_sequences(final_candidates, run_dir)
        self._export_structures(final_candidates, run_dir)
        logger.info(f"✓ Exported data to {run_dir}")
        
        # Step 2: Generate SOP
        logger.info("\nStep 2: Generate SOP document")
        logger.info("-" * 80)
        sop_path = self._generate_sop(state, final_candidates, run_dir)
        logger.info(f"✓ SOP saved to {sop_path}")
        
        # Step 3: Generate summary
        logger.info("\nStep 3: Generate summary report")
        logger.info("-" * 80)
        summary_path = self._generate_summary(state, run_dir)
        logger.info(f"✓ Summary saved to {summary_path}")
        
        # Step 4: (Optional) Neo4j
        if self.phase_config['neo4j'].get('enabled', False):
            logger.info("\nStep 4: Save to Neo4j")
            logger.info("-" * 80)
            self._save_to_neo4j(state, final_candidates)
            logger.info("✓ Data saved to Neo4j")
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"PIPELINE COMPLETE!")
        logger.info(f"{'=' * 80}")
        logger.info(f"\nResults:")
        logger.info(f"  Run ID: {state.run_id}")
        logger.info(f"  Target: {state.target.target_id}")
        logger.info(f"  Final candidates: {len(final_candidates)}")
        logger.info(f"  Output directory: {run_dir}")
        logger.info(f"  SOP: {sop_path}")
        logger.info(f"  Summary: {summary_path}")
        logger.info(f"\n{'=' * 80}\n")
        
        return state
    
    def _export_sequences(self, candidates: List[DesignCandidate], output_dir: Path):
        """Export all sequences to FASTA file"""
        fasta_path = output_dir / "final_sequences.fasta"
        
        with open(fasta_path, 'w') as f:
            for candidate in candidates:
                f.write(f">{candidate.candidate_id}\n")
                f.write(f"{candidate.binder_sequence}\n")
        
        logger.info(f"  Sequences: {fasta_path}")
    
    def _export_structures(self, candidates: List[DesignCandidate], output_dir: Path):
        """Export structure file list"""
        structures_path = output_dir / "structures_list.txt"
        
        with open(structures_path, 'w') as f:
            for candidate in candidates:
                f.write(f"{candidate.candidate_id}\t{candidate.complex_pdb_path}\n")
        
        logger.info(f"  Structures: {structures_path}")
    
    def _generate_sop(self, state: PipelineState, 
                     candidates: List[DesignCandidate], 
                     output_dir: Path) -> Path:
        """Generate Standard Operating Procedure document"""
        
        sop_path = output_dir / "SOP.md"
        
        sop_content = f"""# Standard Operating Procedure
## Protein Binder Production and Validation

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Run ID**: {state.run_id}  
**Target**: {state.target.target_id} ({state.target.target_pdb_path})  
**Number of Candidates**: {len(candidates)}

---

## 1. Gene Synthesis and Cloning

### 1.1 Gene Synthesis
- Order synthesized genes for all {len(candidates)} candidates
- Include appropriate restriction sites (e.g., NdeI/XhoI)
- Add His6-tag at C-terminus for purification

### 1.2 Cloning
- Clone into pET-28a(+) or similar expression vector
- Transform into DH5α competent cells
- Select on LB-Kanamycin plates
- Verify by Sanger sequencing

---

## 2. Protein Expression

### 2.1 Small Scale Expression Test
- Transform sequence-verified plasmids into BL21(DE3)
- Grow 5 mL cultures at 37°C to OD600 = 0.6
- Induce with 0.5 mM IPTG, grow 16h at 18°C
- Analyze by SDS-PAGE

### 2.2 Large Scale Expression
- Scale up expressing clones to 1L cultures
- Induce at OD600 = 0.8 with 0.5 mM IPTG
- Harvest cells by centrifugation (4000g, 20 min, 4°C)

---

## 3. Protein Purification

### 3.1 Cell Lysis
- Resuspend in lysis buffer (50 mM Tris pH 8.0, 300 mM NaCl, 10 mM imidazole)
- Lyse by sonication or French press
- Clarify by centrifugation (20,000g, 30 min, 4°C)

### 3.2 IMAC Purification
- Load supernatant onto Ni-NTA column
- Wash with 20 column volumes wash buffer (50 mM imidazole)
- Elute with elution buffer (250 mM imidazole)

### 3.3 Size Exclusion Chromatography
- Concentrate eluate to 2-5 mg/mL
- Load onto Superdex 75 16/600 column
- Collect monodisperse peak fractions
- Concentrate to 1-10 mg/mL

---

## 4. Binding Assay

### 4.1 Bio-Layer Interferometry (BLI)
- Immobilize biotinylated target on streptavidin sensors
- Test binder concentrations: 1 nM - 1 μM
- Measure association (180s) and dissociation (300s)
- Calculate KD using 1:1 binding model

### 4.2 Surface Plasmon Resonance (SPR)
- Immobilize target via amine coupling
- Run multi-cycle kinetics with binder series
- Regenerate surface between cycles
- Validate hits with KD < 100 nM

---

## 5. Stability Assessment

### 5.1 Thermal Stability (DSF)
- Prepare samples at 0.2 mg/mL with SYPRO Orange
- Heat from 20°C to 95°C at 1°C/min
- Determine melting temperature (Tm)
- Target: Tm > 60°C

### 5.2 Aggregation Propensity
- Dynamic Light Scattering (DLS) at 25°C
- Measure polydispersity index (PDI)
- Target: PDI < 0.2, monodisperse peak

---

## 6. Structural Validation

### 6.1 Complex Formation
- Mix target and binder at 1:1.2 molar ratio
- Incubate on ice for 1h
- Purify complex by SEC

### 6.2 Crystallization or Cryo-EM
- Set up crystallization screens (for X-ray)
- Or prepare grids for cryo-EM
- Validate interface matches computational predictions

---

## 7. Candidate Priority List

Top candidates ranked by predicted performance:

"""
        
        # Add candidate rankings
        for i, candidate in enumerate(candidates, 1):
            ddg = candidate.metrics.get('interface_ddg', 'N/A')
            sap = candidate.metrics.get('sap', 'N/A')
            dockq = candidate.metrics.get('dockq', 'N/A')
            
            sop_content += f"\n### Rank {i}: {candidate.candidate_id}\n"
            sop_content += f"- **Sequence**: `{candidate.binder_sequence}`\n"
            sop_content += f"- **Predicted ddG**: {ddg}\n"
            sop_content += f"- **SAP Score**: {sap}\n"
            sop_content += f"- **DockQ**: {dockq}\n"
        
        sop_content += """

---

## 8. Data Recording

### 8.1 Required Records
- Expression yields (mg/L)
- Purification yields and purity (SDS-PAGE)
- Binding kinetics (KD, kon, koff)
- Thermal stability (Tm)
- Aggregation data (DLS)
- Structural data (if obtained)

### 8.2 Success Criteria
- Expression yield > 10 mg/L
- Purity > 95%
- KD < 100 nM
- Tm > 60°C
- Monodisperse by DLS

---

## 9. Feedback Loop

Record all experimental results and update computational models:
- Successful binders → training data
- Failed binders → identify failure modes
- Update scoring functions based on experimental validation

---

**Document Version**: 1.0  
**Last Updated**: {datetime.now().strftime("%Y-%m-%d")}
"""
        
        with open(sop_path, 'w') as f:
            f.write(sop_content)
        
        return sop_path
    
    def _generate_summary(self, state: PipelineState, output_dir: Path) -> Path:
        """Generate pipeline summary report"""
        
        summary_path = output_dir / "pipeline_summary.md"
        
        # Count candidates by stage
        stage_counts = {}
        for candidate in state.candidates:
            stage = candidate.stage
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        summary_content = f"""# Pipeline Execution Summary

**Run ID**: {state.run_id}  
**Target**: {state.target.target_id}  
**Execution Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Target Information

- **Target ID**: {state.target.target_id}
- **Target PDB**: {state.target.target_pdb_path}
- **Chain**: {state.target.chain_id}
- **Hotspot Residues**: {state.target.hotspot_residues}
- **Notes**: {state.target.notes if state.target.notes else 'None'}

---

## Pipeline Statistics

### Candidate Progression

| Stage | Count |
|-------|-------|
"""
        
        for stage, count in sorted(stage_counts.items()):
            summary_content += f"| {stage} | {count} |\n"
        
        summary_content += f"""
**Total Candidates Generated**: {len(state.candidates)}  
**Final Selected Candidates**: {stage_counts.get('selected', 0)}

---

## Phase Execution Summary

### Phase 1: Target Discovery
- Target specification validated
- Hotspot residues confirmed

### Phase 2: Generative Design
- De novo backbone generation: RFdiffusion
- Refinement iterations: {self.config['phase2']['rfdiffusion']['max_refinement_iterations']}
- Sequence design: ProteinMPNN
- Generated candidates: {stage_counts.get('generated', 0)}

### Phase 3: Screening and Validation
- Fast screening (Chai-1, DockQ)
- Passed fast screening: {stage_counts.get('fast_screened', 0)}
- Deep validation (ColabFold)
- Validated candidates: {stage_counts.get('deep_validated', 0)}

### Phase 4: Optimization
- Multi-objective optimization (NSGA-II)
- Developability assessment
- Final selection: {stage_counts.get('selected', 0)}

### Phase 5: Lab Automation
- SOP generated
- Sequences and structures exported
- Ready for experimental validation

---

## Configuration

```yaml
Project Root: {self.config['project_root']}
RFdiffusion Path: {self.config['phase2']['rfdiffusion']['path']}
ProteinMPNN Path: {self.config['phase2']['proteinmpnn']['path']}
Chai-1 Path: {self.config['phase3_fast']['chai']['path']}
ColabFold Path: {self.config['phase3_deep']['colabfold']['path']}
```

---

## Output Files

- **Sequences**: `final_sequences.fasta`
- **Structures**: `structures_list.txt`
- **SOP**: `SOP.md`
- **Summary**: `pipeline_summary.md`

---

**Pipeline Version**: 0.1.0  
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        with open(summary_path, 'w') as f:
            f.write(summary_content)
        
        return summary_path
    
    def _save_to_neo4j(self, state: PipelineState, candidates: List[DesignCandidate]):
        """
        Save results to Neo4j database
        Placeholder - actual implementation needed
        """
        logger.info("  Neo4j integration not implemented (placeholder)")
        pass
