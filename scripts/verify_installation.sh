#!/bin/bash

set -e

echo "=========================================="
echo "Quick Installation Test"
echo "=========================================="
echo ""

PROJECT_ROOT="/home01/hpc194a02/test/sim_pip"
cd "$PROJECT_ROOT"

echo "[1/5] Checking Python environment..."
echo ""

if [ ! -d ".venv" ]; then
    echo "ERROR: .venv not found. Please run setup.sh first."
    exit 1
fi

source .venv/bin/activate
echo "✓ Virtual environment activated."
echo ""

echo "[2/5] Checking SE3nv environment..."
echo ""

if ! conda env list | grep -q "SE3nv"; then
    echo "ERROR: SE3nv environment not found."
    exit 1
fi
echo "✓ SE3nv environment exists."
echo ""

echo "[3/5] Checking installed tools..."
echo ""

ERRORS=0

# Check RFdiffusion
if [ -f "tools/rfdiffusion/scripts/run_inference.py" ]; then
    echo "✓ RFdiffusion found."
else
    echo "✗ RFdiffusion not found."
    ERRORS=$((ERRORS + 1))
fi

# Check ProteinMPNN
if [ -f "tools/proteinmpnn/protein_mpnn_run.py" ]; then
    echo "✓ ProteinMPNN found."
else
    echo "✗ ProteinMPNN not found."
    ERRORS=$((ERRORS + 1))
fi

# Check Chai-1
if command -v chai-lab &> /dev/null; then
    echo "✓ Chai-1 installed."
else
    echo "✗ Chai-1 not installed."
    ERRORS=$((ERRORS + 1))
fi

# Check ColabFold
if [ -d "tools/colabfold" ]; then
    echo "✓ ColabFold directory exists."
else
    echo "✗ ColabFold not found."
    ERRORS=$((ERRORS + 1))
fi

# Check DockQ
if command -v DockQ &> /dev/null; then
    echo "✓ DockQ installed."
else
    echo "⚠ DockQ not installed (optional)."
fi

# Check kalign
if command -v kalign &> /dev/null; then
    echo "✓ kalign installed."
else
    echo "⚠ kalign not installed (optional)."
fi

echo ""

echo "[4/5] Checking models..."
echo ""

if [ -f "tools/rfdiffusion/models/Complex_base_ckpt.pt" ]; then
    MODEL_SIZE=$(du -h tools/rfdiffusion/models/Complex_base_ckpt.pt | cut -f1)
    echo "✓ RFdiffusion model exists ($MODEL_SIZE)"
else
    echo "✗ RFdiffusion model not found."
    ERRORS=$((ERRORS + 1))
fi

echo ""

echo "[5/5] Checking directory structure..."
echo ""

DIRS=(
    "data/inputs/pdb"
    "data/outputs/rfdiffusion"
    "data/candidates"
    "data/runs"
    "logs"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ $dir"
    else
        echo "✗ $dir missing"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "=========================================="

if [ $ERRORS -eq 0 ]; then
    echo "✓ All checks passed!"
    echo "=========================================="
    echo ""
    echo "You can now run:"
    echo "  python main.py --target-pdb target.pdb --interactive"
    echo ""
    exit 0
else
    echo "✗ $ERRORS error(s) found."
    echo "=========================================="
    echo ""
    echo "Please run: bash setup.sh"
    echo ""
    exit 1
fi
