#!/bin/bash

set -e

echo "=========================================="
echo "RFdiffusion Setup Test"
echo "=========================================="
echo ""

PROJECT_ROOT="/home01/hpc194a02/test/sim_pip"
cd "$PROJECT_ROOT"

echo "[1/4] Checking SE3nv environment..."
echo ""

if ! conda env list | grep -q "SE3nv"; then
    echo "ERROR: SE3nv environment not found."
    echo "Please run: conda env create -f tools/rfdiffusion/env/SE3nv.yml"
    exit 1
fi
echo "✓ SE3nv environment exists."
echo ""

echo "[2/4] Checking RFdiffusion models..."
echo ""

if [ ! -f "tools/rfdiffusion/models/Complex_base_ckpt.pt" ]; then
    echo "ERROR: Complex_base_ckpt.pt not found."
    echo "Please run the setup script or download manually:"
    echo "  cd tools/rfdiffusion/models"
    echo "  wget http://files.ipd.uw.edu/pub/RFdiffusion/e29311f6f1bf1af907f9ef9f44b8328b/Complex_base_ckpt.pt"
    exit 1
fi

MODEL_SIZE=$(du -h tools/rfdiffusion/models/Complex_base_ckpt.pt | cut -f1)
echo "✓ Complex_base_ckpt.pt exists ($MODEL_SIZE)"
echo ""

echo "[3/4] Checking test files..."
echo ""

if [ ! -f "tests/test_rfdiffusion/target.pdb" ]; then
    echo "ERROR: Test target PDB not found at tests/test_rfdiffusion/target.pdb"
    exit 1
fi
echo "✓ Test PDB file exists."
echo ""

echo "[4/4] Running RFdiffusion test..."
echo ""

# Activate SE3nv environment
eval "$(conda shell.bash hook)"
conda activate SE3nv

# Create output directory
mkdir -p tests/test_rfdiffusion/outputs

# Run a quick test with 1 design
cd tests/test_rfdiffusion
python ../../tools/rfdiffusion/scripts/run_inference.py \
  inference.input_pdb=target.pdb \
  inference.output_prefix=outputs/binder \
  inference.num_designs=1 \
  'contigmap.contigs=[A1-150/0 80-80]' \
  'ppi.hotspot_res=[A982,A990,A995]'

cd "$PROJECT_ROOT"

if [ -f "tests/test_rfdiffusion/outputs/binder_0.pdb" ]; then
    echo ""
    echo "✓ Test successful! Output generated at:"
    ls -lh tests/test_rfdiffusion/outputs/binder_*.pdb
    echo ""
    echo "=========================================="
    echo "RFdiffusion is ready to use!"
    echo "=========================================="
else
    echo ""
    echo "ERROR: Test failed. No output generated."
    exit 1
fi

conda deactivate
