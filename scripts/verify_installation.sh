#!/bin/bash

# Installation Verification Script
# Checks if all required components are properly installed

set +e  # Don't exit on errors, we want to check everything

echo "=========================================="
echo "Installation Verification"
echo "=========================================="
echo ""

ERRORS=0
WARNINGS=0

# Color codes (if terminal supports it)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored status
print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
        ((WARNINGS++))
    else
        echo -e "${RED}✗${NC} $message"
        ((ERRORS++))
    fi
}

echo "[1/7] Checking Python environment..."
echo ""

# Check Python
if command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1)
    print_status "OK" "Python: $PYTHON_VERSION"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    print_status "OK" "Python3: $PYTHON_VERSION"
else
    print_status "ERROR" "Python not found"
fi

# Check venv
if [ -d ".venv" ]; then
    print_status "OK" "Virtual environment (.venv) exists"
    
    # Activate and check packages
    source .venv/bin/activate
    
    # Check core Python packages
    python -c "import torch; print(f'PyTorch {torch.__version__}')" 2>/dev/null && \
        print_status "OK" "PyTorch installed in venv" || \
        print_status "ERROR" "PyTorch not found in venv"
    
    python -c "import numpy" 2>/dev/null && \
        print_status "OK" "NumPy installed in venv" || \
        print_status "ERROR" "NumPy not found in venv"
    
    python -c "import pandas" 2>/dev/null && \
        print_status "OK" "Pandas installed in venv" || \
        print_status "WARN" "Pandas not found in venv"
    
    python -c "import Bio" 2>/dev/null && \
        print_status "OK" "BioPython installed in venv" || \
        print_status "WARN" "BioPython not found in venv"
    
    python -c "import yaml" 2>/dev/null && \
        print_status "OK" "PyYAML installed in venv" || \
        print_status "ERROR" "PyYAML not found in venv"
else
    print_status "ERROR" "Virtual environment (.venv) not found"
fi

echo ""
echo "[2/7] Checking Conda environments..."
echo ""

if command -v conda &> /dev/null || [ -f "$HOME/miniconda3/bin/conda" ]; then
    CONDA_CMD=$HOME/miniconda3/bin/conda
    print_status "OK" "Conda found: $($CONDA_CMD --version)"
    
    # Check SE3nv environment
    if $CONDA_CMD env list | grep -q "SE3nv"; then
        print_status "OK" "SE3nv environment exists (for RFdiffusion)"
    else
        print_status "ERROR" "SE3nv environment not found"
    fi
    
    # Check boltz_env environment
    if $CONDA_CMD env list | grep -q "boltz_env"; then
        print_status "OK" "boltz_env environment exists (for Boltz)"
        
        # Check if PyTorch is in boltz_env
        if $HOME/miniconda3/envs/boltz_env/bin/python -c "import torch" 2>/dev/null; then
            print_status "OK" "PyTorch installed in boltz_env"
        else
            print_status "ERROR" "PyTorch not found in boltz_env"
        fi
    else
        print_status "ERROR" "boltz_env environment not found"
    fi
    
    # Check PyRosetta
    if $HOME/miniconda3/bin/python -c "import pyrosetta" 2>/dev/null; then
        print_status "OK" "PyRosetta installed in conda base"
    else
        print_status "WARN" "PyRosetta not found (optional)"
    fi
else
    print_status "ERROR" "Conda not found"
fi

echo ""
echo "[3/7] Checking system tools..."
echo ""

# Check kalign
if command -v kalign &> /dev/null || [ -f "$HOME/miniconda3/bin/kalign" ]; then
    KALIGN_VERSION=$(kalign --version 2>&1 | head -n1 || $HOME/miniconda3/bin/kalign --version 2>&1 | head -n1)
    print_status "OK" "kalign: $KALIGN_VERSION"
else
    print_status "WARN" "kalign not found (optional)"
fi

# Check DockQ
if command -v DockQ &> /dev/null; then
    print_status "OK" "DockQ installed"
else
    print_status "WARN" "DockQ not found (optional)"
fi

# Check GPU
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null)
    if [ -n "$GPU_NAME" ]; then
        print_status "OK" "GPU: $GPU_NAME"
    else
        print_status "WARN" "nvidia-smi found but GPU not detected"
    fi
else
    print_status "WARN" "nvidia-smi not found (GPU may not be available)"
fi

echo ""
echo "[4/7] Checking tool directories..."
echo ""

TOOLS_DIR="./tools"

# Check RFdiffusion
if [ -d "$TOOLS_DIR/rfdiffusion" ]; then
    print_status "OK" "RFdiffusion directory exists"
    
    if [ -d "$TOOLS_DIR/rfdiffusion/models" ] && [ "$(ls -A $TOOLS_DIR/rfdiffusion/models)" ]; then
        print_status "OK" "RFdiffusion models directory contains files"
    else
        print_status "WARN" "RFdiffusion models directory empty"
    fi
else
    print_status "ERROR" "RFdiffusion directory not found"
fi

# Check Boltz
if [ -d "$TOOLS_DIR/boltz" ]; then
    print_status "OK" "Boltz directory exists"
else
    print_status "ERROR" "Boltz directory not found"
fi

# Check Chai-1
if [ -d "$TOOLS_DIR/chai-1" ]; then
    print_status "OK" "Chai-1 directory exists"
else
    print_status "WARN" "Chai-1 directory not found"
fi

# Check ProteinMPNN
if [ -d "$TOOLS_DIR/proteinmpnn" ]; then
    print_status "OK" "ProteinMPNN directory exists"
else
    print_status "WARN" "ProteinMPNN directory not found"
fi

echo ""
echo "[5/7] Checking data directories..."
echo ""

# Check required directories
REQUIRED_DIRS=(
    "data/inputs/pdb"
    "data/inputs/fasta"
    "data/outputs/rfdiffusion"
    "data/outputs/proteinmpnn"
    "data/outputs/chai1"
    "data/outputs/boltz"
    "data/candidates"
    "logs"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        print_status "OK" "$dir exists"
    else
        print_status "WARN" "$dir not found"
    fi
done

echo ""
echo "[6/7] Checking configuration files..."
echo ""

if [ -f "requirements.txt" ]; then
    print_status "OK" "requirements.txt exists"
else
    print_status "ERROR" "requirements.txt not found"
fi

if [ -f "main.py" ]; then
    print_status "OK" "main.py exists"
else
    print_status "ERROR" "main.py not found"
fi

if [ -d "pipeline" ]; then
    print_status "OK" "pipeline directory exists"
else
    print_status "ERROR" "pipeline directory not found"
fi

echo ""
echo "[7/7] Testing imports..."
echo ""

source .venv/bin/activate 2>/dev/null

# Test key imports
python -c "
import sys
try:
    import torch
    print('✓ PyTorch import successful')
    print(f'  - CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'  - CUDA version: {torch.version.cuda}')
except ImportError as e:
    print(f'✗ PyTorch import failed: {e}')
    sys.exit(1)

try:
    import numpy
    import pandas
    import yaml
    print('✓ Core scientific packages import successful')
except ImportError as e:
    print(f'✗ Import failed: {e}')
    sys.exit(1)
" 2>&1

if [ $? -eq 0 ]; then
    print_status "OK" "Python imports working"
else
    print_status "ERROR" "Python imports failed"
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Your installation is complete and ready to use."
    echo ""
    echo "Next steps:"
    echo "  1. Activate the environment: source .venv/bin/activate"
    echo "  2. Run the pipeline: python main.py --help"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Installation complete with $WARNINGS warning(s)${NC}"
    echo ""
    echo "Core functionality should work, but some optional features may be unavailable."
    echo ""
    echo "To resolve warnings:"
    echo "  - For missing tools: Run setup_linux.sh again"
    echo "  - For GPU issues: Check NVIDIA drivers"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Installation incomplete: $ERRORS error(s), $WARNINGS warning(s)${NC}"
    echo ""
    echo "Please review the errors above and:"
    echo "  1. Run setup_linux.sh again"
    echo "  2. Check the installation logs"
    echo "  3. Refer to INSTALLATION.md for troubleshooting"
    echo ""
    exit 1
fi
