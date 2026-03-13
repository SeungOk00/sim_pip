#!/bin/bash

# Quick RFdiffusion Test (CPU-friendly)
# Tests if RFdiffusion can run with minimal resources

set -e

echo "=========================================="
echo "RFdiffusion Quick Test (CPU Mode)"
echo "=========================================="
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate SE3nv environment
echo "[1/4] Activating SE3nv environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate SE3nv

# Check if example PDB exists
EXAMPLE_PDB="tools/rfdiffusion/examples/input_pdbs/insulin_target.pdb"
if [ ! -f "$EXAMPLE_PDB" ]; then
    echo "ERROR: Example PDB not found at $EXAMPLE_PDB"
    exit 1
fi
echo "✓ Using example PDB: $EXAMPLE_PDB"

# Create output directory
OUTPUT_DIR="/tmp/rfdiff_test_$(date +%s)"
mkdir -p "$OUTPUT_DIR"
echo "✓ Output directory: $OUTPUT_DIR"

# Run RFdiffusion with minimal settings
echo ""
echo "[2/4] Running RFdiffusion (1 design, small target)..."
echo "This may take 5-15 minutes on CPU..."
echo ""

cd tools/rfdiffusion

PYTHONPATH="$PWD:$PWD/env/SE3Transformer" \
python scripts/run_inference.py \
    inference.input_pdb="$EXAMPLE_PDB" \
    inference.output_prefix="$OUTPUT_DIR/test" \
    inference.num_designs=1 \
    'contigmap.contigs=[A1-50/0 40-40]' \
    2>&1 | tee "$OUTPUT_DIR/rfdiffusion.log"

EXIT_CODE=${PIPESTATUS[0]}

cd ../..

echo ""
echo "[3/4] Checking results..."

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ RFdiffusion completed successfully!"
    
    # Check output files
    OUTPUT_FILES=$(ls -1 "$OUTPUT_DIR"/test_*.pdb 2>/dev/null | wc -l)
    if [ "$OUTPUT_FILES" -gt 0 ]; then
        echo "✓ Generated $OUTPUT_FILES PDB file(s)"
        ls -lh "$OUTPUT_DIR"/test_*.pdb
    else
        echo "⚠ Warning: No PDB files found in output"
    fi
else
    echo "✗ RFdiffusion failed with exit code $EXIT_CODE"
    echo ""
    echo "Check log file: $OUTPUT_DIR/rfdiffusion.log"
    echo ""
    echo "Common issues:"
    echo "  1. GPU not available - RFdiffusion may fail on CPU"
    echo "  2. Out of memory - try smaller contig"
    echo "  3. Missing dependencies - check SE3nv environment"
    exit 1
fi

echo ""
echo "[4/4] Summary"
echo "=========================================="
echo "Output directory: $OUTPUT_DIR"
echo "Log file: $OUTPUT_DIR/rfdiffusion.log"
echo ""
echo "Next steps:"
echo "  - To enable GPU: See docs/GPU_SETUP_WSL2.md"
echo "  - To run full pipeline: python scripts/test_phase1_2_3.py"
echo "=========================================="

conda deactivate
