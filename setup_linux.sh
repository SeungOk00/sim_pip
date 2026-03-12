#!/bin/bash

set -e

echo "=========================================="
echo "Protein Binder Design Pipeline Setup (Linux)"
echo "=========================================="
echo ""

# Set project root to absolute path
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "[1/10] Checking system requirements..."
echo ""

if ! command -v nvidia-smi &> /dev/null; then
    echo "WARNING: nvidia-smi not found. GPU may not be available."
else
    echo "✓ GPU detected:"
    nvidia-smi --query-gpu=name --format=csv,noheader
fi

if ! command -v python &> /dev/null; then
    echo "ERROR: python not found."
    exit 1
fi
echo "✓ Python version: $(python --version)"
echo ""

echo "[2/10] Installing Miniconda (if not already installed)..."
echo ""

if ! command -v conda &> /dev/null; then
    echo "Conda not found. Installing Miniconda..."
    
    MINICONDA_DIR="$HOME/miniconda3"
    
    if [ -d "$MINICONDA_DIR" ]; then
        echo "Miniconda directory already exists at $MINICONDA_DIR"
        
        # Initialize conda for this session
        if [ -f "$MINICONDA_DIR/etc/profile.d/conda.sh" ]; then
            source "$MINICONDA_DIR/etc/profile.d/conda.sh"
        fi
        export PATH="$MINICONDA_DIR/bin:$PATH"
        
        # Check if conda is now accessible
        if command -v conda &> /dev/null; then
            echo "✓ Conda is accessible: $(conda --version)"
        else
            echo "WARNING: Conda installed but not accessible. Trying to initialize..."
            "$MINICONDA_DIR/bin/conda" init bash 2>/dev/null || true
            echo "Please restart your terminal and run this script again."
            exit 0
        fi
        
        read -p "Do you want to reinstall? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "✓ Using existing Miniconda."
        else
            rm -rf "$MINICONDA_DIR"
        fi
    fi
    
    if [ ! -d "$MINICONDA_DIR" ]; then
        # Detect OS
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # Check if Apple Silicon or Intel
            if [[ $(uname -m) == "arm64" ]]; then
                MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
            else
                MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
            fi
        else
            echo "ERROR: Unsupported OS type: $OSTYPE"
            echo "Please manually install Miniconda from: https://docs.conda.io/en/latest/miniconda.html"
            exit 1
        fi
        
        echo "Downloading Miniconda from $MINICONDA_URL..."
        MINICONDA_INSTALLER="/tmp/miniconda_installer.sh"
        
        if command -v wget &> /dev/null; then
            wget -O "$MINICONDA_INSTALLER" "$MINICONDA_URL"
        elif command -v curl &> /dev/null; then
            curl -o "$MINICONDA_INSTALLER" "$MINICONDA_URL"
        else
            echo "ERROR: Neither wget nor curl found. Please install one of them."
            exit 1
        fi
        
        echo "Installing Miniconda to $MINICONDA_DIR..."
        bash "$MINICONDA_INSTALLER" -b -p "$MINICONDA_DIR"
        rm "$MINICONDA_INSTALLER"
        
        # Initialize conda for bash
        "$MINICONDA_DIR/bin/conda" init bash
        
        # Add to current PATH
        export PATH="$MINICONDA_DIR/bin:$PATH"
        eval "$(conda shell.bash hook)"
        
        echo "✓ Miniconda installed successfully."
        echo ""
        echo "IMPORTANT: Please restart your terminal and run this script again."
        echo "Alternatively, run: source ~/.bashrc"
        exit 0
    fi
else
    echo "✓ Conda already installed: $(conda --version)"
fi
echo ""

echo "[3/10] Setting up RFdiffusion environment (SE3nv)..."
echo ""

# Accept conda ToS automatically
if command -v conda &> /dev/null; then
    conda config --set channel_priority flexible 2>/dev/null || true
fi

if conda env list | grep -q "SE3nv"; then
    echo "SE3nv environment already exists."
    read -p "Do you want to recreate it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        conda env remove -n SE3nv -y
        yes | conda env create -f tools/rfdiffusion/env/SE3nv.yml || conda env create -f tools/rfdiffusion/env/SE3nv.yml
        echo "✓ SE3nv environment recreated."
        
        # Install SE3-Transformer
        echo "Installing SE3-Transformer..."
        eval "$(conda shell.bash hook)"
        conda activate SE3nv
        cd tools/rfdiffusion/env/SE3Transformer
        pip install --no-cache-dir -r requirements.txt
        python setup.py install
        cd ../../../..
        
        # Install RFdiffusion module
        cd tools/rfdiffusion
        pip install -e .
        cd ../..
        
        conda deactivate
        echo "✓ SE3-Transformer and RFdiffusion installed."
    else
        echo "✓ Using existing SE3nv environment."
    fi
else
    yes | conda env create -f tools/rfdiffusion/env/SE3nv.yml || conda env create -f tools/rfdiffusion/env/SE3nv.yml
    echo "✓ SE3nv environment created."
    
    # Install SE3-Transformer
    echo "Installing SE3-Transformer..."
    eval "$(conda shell.bash hook)"
    conda activate SE3nv
    cd tools/rfdiffusion/env/SE3Transformer
    pip install --no-cache-dir -r requirements.txt
    python setup.py install
    cd ../../../..
    
    # Install RFdiffusion module
    cd tools/rfdiffusion
    pip install -e .
    cd ../..
    
    conda deactivate
    echo "✓ SE3-Transformer and RFdiffusion installed."
fi
echo ""

echo "[4/10] Downloading RFdiffusion models..."
echo ""

MODEL_DIR="$PROJECT_ROOT/tools/rfdiffusion/models"
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

# Define all model URLs
declare -A models=(
    ["Base_ckpt.pt"]="http://files.ipd.uw.edu/pub/RFdiffusion/6f5902ac237024bdd0c176cb93063dc4/Base_ckpt.pt"
    ["Complex_base_ckpt.pt"]="http://files.ipd.uw.edu/pub/RFdiffusion/e29311f6f1bf1af907f9ef9f44b8328b/Complex_base_ckpt.pt"
    ["Complex_Fold_base_ckpt.pt"]="http://files.ipd.uw.edu/pub/RFdiffusion/60f09a193fb5e5ccdc4980417708dbab/Complex_Fold_base_ckpt.pt"
    ["InpaintSeq_ckpt.pt"]="http://files.ipd.uw.edu/pub/RFdiffusion/74f51cfb8b440f50d70878e05361d8f0/InpaintSeq_ckpt.pt"
    ["InpaintSeq_Fold_ckpt.pt"]="http://files.ipd.uw.edu/pub/RFdiffusion/76d00716416567174cdb7ca96e208296/InpaintSeq_Fold_ckpt.pt"
    ["ActiveSite_ckpt.pt"]="http://files.ipd.uw.edu/pub/RFdiffusion/5532d2e1f3a4738decd58b19d633b3c3/ActiveSite_ckpt.pt"
    ["Base_epoch8_ckpt.pt"]="http://files.ipd.uw.edu/pub/RFdiffusion/12fc204edeae5b57713c5ad7dcb97d39/Base_epoch8_ckpt.pt"
    ["Complex_beta_ckpt.pt"]="http://files.ipd.uw.edu/pub/RFdiffusion/f572d396fae9206628714fb2ce00f72e/Complex_beta_ckpt.pt"
    ["RF_structure_prediction_weights.pt"]="http://files.ipd.uw.edu/pub/RFdiffusion/1befcb9b28e2f778f53d47f18b7597fa/RF_structure_prediction_weights.pt"
)

# Download each model if not present
for model_name in "${!models[@]}"; do
    if [ -f "$model_name" ]; then
        echo "✓ $model_name already exists."
    else
        echo "Downloading $model_name..."
        url="${models[$model_name]}"
        
        if command -v wget &> /dev/null; then
            wget "$url"
        elif command -v curl &> /dev/null; then
            curl -o "$model_name" "$url"
        else
            echo "ERROR: Neither wget nor curl found. Please install one of them."
            cd "$PROJECT_ROOT"
            exit 1
        fi
        
        if [ -f "$model_name" ]; then
            echo "✓ $model_name downloaded successfully."
        else
            echo "WARNING: Failed to download $model_name"
        fi
    fi
done

cd "$PROJECT_ROOT"
echo ""
echo "✓ All RFdiffusion models downloaded."
echo ""

echo "[5/10] Setting up main Python environment..."
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

# Activate virtual environment
source .venv/bin/activate
echo "✓ Virtual environment activated."

# Upgrade pip using python -m pip
python -m pip install --upgrade pip || echo "WARNING: pip upgrade failed, continuing..."

# Install scipy via conda to avoid compilation issues
echo "Installing scipy via conda..."
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda install -c conda-forge scipy -y
    echo "✓ scipy installed via conda."
else
    echo "WARNING: conda not found, skipping scipy conda install..."
    echo "  You may need to install it manually later."
fi

pip install -r requirements.txt
echo "✓ Dependencies installed."
echo ""

echo "[6/10] Installing Chai-1..."
echo ""

pip install -e ./tools/chai-1
if command -v chai-lab &> /dev/null; then
    echo "✓ Chai-1 installed successfully."
else
    echo "WARNING: chai-lab command not found. Installation may have failed."
fi
echo ""

echo "[7/10] Installing Boltz (separate environment)..."
echo ""

# Boltz requires Python <3.13, create conda environment with Python 3.12
BOLTZ_ENV="boltz_env"

if conda env list | grep -q "$BOLTZ_ENV"; then
    echo "$BOLTZ_ENV environment already exists."
    read -p "Do you want to recreate it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        conda env remove -n $BOLTZ_ENV -y
        conda create -n $BOLTZ_ENV python=3.12 -y
        echo "✓ $BOLTZ_ENV environment recreated with Python 3.12."
    else
        echo "✓ Using existing $BOLTZ_ENV environment."
    fi
else
    conda create -n $BOLTZ_ENV python=3.12 -y
    echo "✓ $BOLTZ_ENV environment created with Python 3.12."
fi

# Activate Boltz conda environment
eval "$(conda shell.bash hook)"
conda activate $BOLTZ_ENV
python -m pip install --upgrade pip || echo "WARNING: pip upgrade failed, continuing..."
pip install -e ./tools/boltz

if command -v boltz &> /dev/null; then
    echo "✓ Boltz installed successfully."
else
    echo "WARNING: boltz command not found. Installation may have failed."
fi

conda deactivate
# Reactivate main venv
source .venv/bin/activate
echo ""

echo "[8/10] Installing PyRosetta..."
echo ""

# Linux/macOS - Install PyRosetta via conda
echo "Installing PyRosetta via conda..."
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    # Use WEST coast mirror (default)
    conda install -y -c https://conda.rosettacommons.org -c conda-forge pyrosetta || \
    # Fallback to EAST coast mirror
    conda install -y -c https://conda.graylab.jhu.edu -c conda-forge pyrosetta
    
    if python -c "import pyrosetta" 2>/dev/null; then
        echo "✓ PyRosetta installed successfully."
    else
        echo "WARNING: PyRosetta installation may have failed."
        echo "You can try manual installation with:"
        echo "  conda install -c https://conda.rosettacommons.org -c conda-forge pyrosetta"
    fi
else
    echo "WARNING: Conda not found. Trying pip method..."
    pip install pyrosetta-installer
    python -c 'import pyrosetta_installer; pyrosetta_installer.install_pyrosetta()'
    
    if python -c "import pyrosetta" 2>/dev/null; then
        echo "✓ PyRosetta installed successfully."
    else
        echo "WARNING: PyRosetta installation may have failed."
    fi
fi
echo ""

echo "[9/10] Installing system dependencies..."
echo ""

# kalign
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

# DockQ
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

echo "[10/10] Creating necessary directories..."
echo ""

mkdir -p data/inputs/pdb
mkdir -p data/inputs/fasta
mkdir -p data/outputs/rfdiffusion
mkdir -p data/outputs/proteinmpnn
mkdir -p data/outputs/chai1
mkdir -p data/outputs/boltz
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
echo "  ✓ Boltz (boltz_env environment, Python 3.12)"
echo "  ✓ PyRosetta"
echo "  ✓ System dependencies (kalign, DockQ)"
echo "  ✓ BioPython (for Phase 3 metrics)"
echo ""
echo "Next steps:"
echo "1. Activate the main environment: source .venv/bin/activate"
echo "2. Test RFdiffusion: bash scripts/test_rfdiffusion_setup.sh"
echo "3. Verify installation: bash scripts/verify_installation.sh"
echo "4. Run the pipeline: python main.py --target-pdb target.pdb --interactive"
echo ""
echo "Note: To use RFdiffusion, activate SE3nv: conda activate SE3nv"
echo "      To use Boltz, activate boltz_env: conda activate boltz_env"
echo ""
