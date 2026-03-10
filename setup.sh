#!/bin/bash

set -e

echo "=========================================="
echo "Protein Binder Design Pipeline Setup"
echo "=========================================="
echo ""

PROJECT_ROOT="/home01/hpc194a02/test/sim_pip"
cd "$PROJECT_ROOT"

echo "[1/9] Checking system requirements..."
echo ""

if ! command -v nvidia-smi &> /dev/null; then
    echo "WARNING: nvidia-smi not found. GPU may not be available."
else
    echo "✓ GPU detected:"
    nvidia-smi --query-gpu=name --format=csv,noheader
fi

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found. Please install Anaconda or Miniconda first."
    exit 1
fi
echo "✓ Conda version: $(conda --version)"

if ! command -v python &> /dev/null; then
    echo "ERROR: python not found."
    exit 1
fi
echo "✓ Python version: $(python --version)"
echo ""

echo "[2/9] Setting up RFdiffusion environment (SE3nv)..."
echo ""

if conda env list | grep -q "SE3nv"; then
    echo "SE3nv environment already exists."
    read -p "Do you want to recreate it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        conda env remove -n SE3nv -y
        conda env create -f tools/rfdiffusion/env/SE3nv.yml
        echo "✓ SE3nv environment recreated."
    else
        echo "✓ Using existing SE3nv environment."
    fi
else
    conda env create -f tools/rfdiffusion/env/SE3nv.yml
    echo "✓ SE3nv environment created."
fi
echo ""

echo "[3/9] Downloading RFdiffusion models..."
echo ""

if [ -f "tools/rfdiffusion/models/Complex_base_ckpt.pt" ]; then
    echo "✓ Complex_base_ckpt.pt already exists."
else
    echo "Downloading Complex_base_ckpt.pt (2.1 GB)..."
    mkdir -p tools/rfdiffusion/models
    cd tools/rfdiffusion/models
    
    if command -v wget &> /dev/null; then
        wget http://files.ipd.uw.edu/pub/RFdiffusion/e29311f6f1bf1af907f9ef9f44b8328b/Complex_base_ckpt.pt
    elif command -v curl &> /dev/null; then
        curl -o Complex_base_ckpt.pt \
          http://files.ipd.uw.edu/pub/RFdiffusion/e29311f6f1bf1af907f9ef9f44b8328b/Complex_base_ckpt.pt
    else
        echo "ERROR: Neither wget nor curl found. Please install one of them."
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    echo "✓ Model downloaded successfully."
fi
echo ""

echo "[4/9] Setting up main Python environment..."
echo ""

if [ -d ".venv" ]; then
    echo ".venv already exists."
    read -p "Do you want to recreate it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv
        python -m venv .venv
        echo "✓ .venv recreated."
    else
        echo "✓ Using existing .venv."
    fi
else
    python -m venv .venv
    echo "✓ .venv created."
fi

source .venv/bin/activate
echo "✓ Virtual environment activated."

pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed."
echo ""

echo "[5/9] Installing Chai-1..."
echo ""

pip install -e ./tools/chai-1
if command -v chai-lab &> /dev/null; then
    echo "✓ Chai-1 installed successfully."
else
    echo "WARNING: chai-lab command not found. Installation may have failed."
fi
echo ""

echo "[6/9] Installing Boltz (separate environment)..."
echo ""

if [ -d ".boltz_venv" ]; then
    echo ".boltz_venv already exists."
    read -p "Do you want to recreate it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .boltz_venv
        python -m venv .boltz_venv
        echo "✓ .boltz_venv recreated."
    else
        echo "✓ Using existing .boltz_venv."
    fi
else
    python -m venv .boltz_venv
    echo "✓ .boltz_venv created."
fi

source .boltz_venv/bin/activate
pip install --upgrade pip
pip install -e ./tools/boltz

if command -v boltz &> /dev/null; then
    echo "✓ Boltz installed successfully."
else
    echo "WARNING: boltz command not found. Installation may have failed."
fi

deactivate
source .venv/bin/activate
echo ""

echo "[7/8] Installing PyRosetta..."
echo ""

echo "Installing pyrosetta-installer..."
pip install pyrosetta-installer

echo "Installing PyRosetta (this may take several minutes)..."
python -c 'import pyrosetta_installer; pyrosetta_installer.install_pyrosetta()'

if python -c "import pyrosetta" 2>/dev/null; then
    echo "✓ PyRosetta installed successfully."
else
    echo "WARNING: PyRosetta installation may have failed."
    echo "You can try manual installation later with:"
    echo "  pip install pyrosetta-installer"
    echo "  python -c 'import pyrosetta_installer; pyrosetta_installer.install_pyrosetta()'"
fi
echo ""

echo "[8/8] Installing system dependencies..."
echo ""

if command -v kalign &> /dev/null; then
    echo "✓ kalign already installed: $(kalign --version 2>&1 | head -n 1)"
else
    echo "Installing kalign via conda..."
    conda install -c bioconda kalign -y
    if command -v kalign &> /dev/null; then
        echo "✓ kalign installed."
    else
        echo "WARNING: kalign installation failed. You may need to install it manually."
    fi
fi

if command -v DockQ &> /dev/null; then
    echo "✓ DockQ already installed."
else
    echo "Installing DockQ..."
    pip install DockQ
    if command -v DockQ &> /dev/null; then
        echo "✓ DockQ installed."
    else
        echo "WARNING: DockQ installation failed."
    fi
fi
echo ""

echo "[9/9] Creating necessary directories..."
echo ""

mkdir -p data/inputs/pdb
mkdir -p data/inputs/fasta
mkdir -p data/outputs/rfdiffusion
mkdir -p data/outputs/proteinmpnn
mkdir -p data/outputs/chai1
mkdir -p data/outputs/colabfold
mkdir -p data/outputs/phase3_fast
mkdir -p data/candidates
mkdir -p data/runs
mkdir -p logs
echo "✓ Directories created."
echo ""

echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Installed components:"
echo "  ✓ RFdiffusion (SE3nv environment)"
echo "  ✓ Main pipeline (.venv)"
echo "  ✓ Chai-1"
echo "  ✓ Boltz (.boltz_venv)"
echo "  ✓ PyRosetta"
echo "  ✓ System dependencies (kalign, DockQ)"
echo ""
echo "Next steps:"
echo "1. Activate the main environment: source .venv/bin/activate"
echo "2. Test RFdiffusion: bash scripts/test_rfdiffusion_setup.sh"
echo "3. Verify installation: bash scripts/verify_installation.sh"
echo "4. Run the pipeline: python main.py --target-pdb target.pdb --interactive"
echo ""
