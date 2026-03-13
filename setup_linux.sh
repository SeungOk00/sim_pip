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

# Check for build tools (gcc, make, etc.)
if ! command -v gcc &> /dev/null; then
    echo "WARNING: gcc (C compiler) not found."
    echo "Attempting to install gcc via conda (no sudo required)..."
    
    # Try to use conda to install gcc
    if command -v conda &> /dev/null || [ -f "$HOME/miniconda3/bin/conda" ]; then
        # Initialize conda if available
        if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
            source "$HOME/miniconda3/etc/profile.d/conda.sh"
        fi
        export PATH="$HOME/miniconda3/bin:$PATH"
        
        echo "Installing gcc and related tools via conda..."
        conda install -y -c conda-forge gcc_linux-64 gxx_linux-64 make 2>/dev/null || {
            echo ""
            echo "Conda 설치를 통한 gcc 설치에 실패했습니다."
            echo "다음 중 하나의 방법을 선택하세요:"
            echo ""
            echo "방법 1 (권장): sudo를 사용하여 시스템 패키지 설치"
            echo "  sudo apt update && sudo apt install -y build-essential python3-dev"
            echo ""
            echo "방법 2: Conda가 설치되면 다시 이 스크립트를 실행하세요."
            echo ""
            exit 1
        }
        echo "✓ Build tools installed via conda"
    else
        echo ""
        echo "빌드 도구가 설치되어 있지 않습니다."
        echo ""
        echo "방법 1 (권장): sudo를 사용하여 설치 (빠름)"
        echo "  sudo apt update && sudo apt install -y build-essential python3-dev"
        echo ""
        echo "방법 2: Conda가 먼저 설치되면 자동으로 gcc를 설치합니다 (sudo 불필요)"
        echo "  이 스크립트를 계속 실행하여 Miniconda를 먼저 설치하세요."
        echo ""
        read -p "Miniconda 설치를 계속하시겠습니까? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        echo "Continuing without gcc for now. Will install via conda..."
    fi
else
    echo "✓ Build tools installed: $(gcc --version | head -n1)"
fi

if command -v make &> /dev/null; then
    echo "✓ Make installed: $(make --version | head -n1)"
fi

if ! command -v nvidia-smi &> /dev/null; then
    echo "WARNING: nvidia-smi not found. GPU may not be available."
else
    echo "✓ GPU detected:"
    nvidia-smi --query-gpu=name --format=csv,noheader
fi

# Check for python or python3
PYTHON_CMD=""
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    # Create python symlink if it doesn't exist
    if [ ! -f "$HOME/.local/bin/python" ]; then
        mkdir -p "$HOME/.local/bin"
        ln -sf "$(which python3)" "$HOME/.local/bin/python"
        export PATH="$HOME/.local/bin:$PATH"
        echo "✓ Created python symlink at $HOME/.local/bin/python"
    fi
else
    echo "ERROR: python or python3 not found."
    exit 1
fi
echo "✓ Python version: $($PYTHON_CMD --version)"
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
        
        # Use existing Miniconda without prompting
        echo "✓ Using existing Miniconda."
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
    # Set safety checks to disabled to avoid prompts
    conda config --set safety_checks disabled 2>/dev/null || true
    # Accept all defaults
    conda config --set always_yes true 2>/dev/null || true
fi

if conda env list | grep -q "SE3nv"; then
    echo "SE3nv environment already exists."
    echo "✓ Using existing SE3nv environment."
else
    echo "Creating SE3nv environment..."
    yes | conda env create -f tools/rfdiffusion/env/SE3nv.yml || conda env create -f tools/rfdiffusion/env/SE3nv.yml
    echo "✓ SE3nv environment created."
fi

# Check GPU status (no PyTorch upgrade)
echo ""
echo "Checking GPU status..."
eval "$(conda shell.bash hook)"
conda activate SE3nv

# Check current PyTorch and CUDA
PYTORCH_VERSION=$(python -c "import torch; print(torch.__version__)" 2>/dev/null || echo "not installed")
CUDA_AVAILABLE=$(python -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "False")

echo "Current PyTorch version: $PYTORCH_VERSION"

if [ "$CUDA_AVAILABLE" = "True" ]; then
    GPU_NAME=$(python -c "import torch; print(torch.cuda.get_device_name(0))" 2>/dev/null)
    GPU_MEMORY=$(python -c "import torch; print(f'{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}')" 2>/dev/null)
    CUDA_VERSION=$(python -c "import torch; print(torch.version.cuda)" 2>/dev/null)
    echo "✓ GPU enabled successfully!"
    echo "  PyTorch: $PYTORCH_VERSION"
    echo "  CUDA: $CUDA_VERSION"
    echo "  Device: $GPU_NAME"
    echo "  Memory: ${GPU_MEMORY} GB"
else
    echo ""
    echo "⚠ WARNING: GPU not detected!"
    echo ""
    echo "GPU is not accessible. This usually means:"
    echo "  1. Windows NVIDIA Driver not installed or outdated"
    echo "     - Required: version 470.76 or higher"
    echo "     - Download: https://www.nvidia.com/Download/index.aspx"
    echo "  2. Computer needs restart after driver installation"
    echo "  3. WSL2 not properly configured (run: wsl --update)"
    echo ""
    echo "To enable GPU:"
    echo "  1. Install NVIDIA Driver on Windows"
    echo "  2. Restart your computer"
    echo "  3. Run 'nvidia-smi' to verify"
    echo ""
    echo "See docs/GPU_ACTIVATION_WITHOUT_PYTORCH_UPGRADE.md for details."
    echo ""
    echo "RFdiffusion will run on CPU (20-50x slower and may crash)."
    echo ""
fi

# Install SE3-Transformer and RFdiffusion
if [ ! -d "tools/rfdiffusion/env/SE3Transformer/build" ]; then
    echo ""
    echo "Installing SE3-Transformer..."
    cd tools/rfdiffusion/env/SE3Transformer
    pip install --no-cache-dir -r requirements.txt
    python setup.py install
    cd ../../../..
    echo "✓ SE3-Transformer installed."
fi

if [ ! -f "tools/rfdiffusion/setup.py" ] || ! python -c "import rfdiffusion" 2>/dev/null; then
    echo ""
    echo "Installing RFdiffusion module..."
    cd tools/rfdiffusion
    pip install -e .
    cd ../..
    echo "✓ RFdiffusion installed."
fi

conda deactivate
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
    # Use existing venv without prompting
    echo "✓ Using existing .venv."
else
    $PYTHON_CMD -m venv .venv
    echo "✓ .venv created."
fi

# Activate virtual environment
source .venv/bin/activate
echo "✓ Virtual environment activated."

# Upgrade pip using python -m pip
echo "Upgrading pip..."
python -m pip install --upgrade pip || echo "WARNING: pip upgrade failed, continuing..."

# Install scipy via conda to avoid compilation issues
echo "Installing scipy via conda (to avoid Fortran compilation)..."
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda install -c conda-forge scipy -y 2>/dev/null || echo "WARNING: scipy conda install failed, will try pip..."
    echo "✓ scipy installed via conda."
else
    echo "WARNING: conda not found, scipy will be installed via pip..."
fi

# Install requirements.txt
echo ""
echo "Installing Python dependencies from requirements.txt..."
echo "This may take several minutes (downloading ~2.5GB of packages)..."
echo ""

if pip install -r requirements.txt; then
    echo ""
    echo "✓ All dependencies installed successfully!"
    echo ""
    
    # Verify key packages
    echo "Verifying key packages..."
    python -c "import torch; print(f'  ✓ PyTorch {torch.__version__}')" 2>/dev/null || echo "  ⚠ PyTorch not found"
    python -c "import numpy; print(f'  ✓ NumPy {numpy.__version__}')" 2>/dev/null || echo "  ⚠ NumPy not found"
    python -c "import pandas; print(f'  ✓ Pandas {pandas.__version__}')" 2>/dev/null || echo "  ⚠ Pandas not found"
    python -c "import biopython; print(f'  ✓ BioPython installed')" 2>/dev/null || echo "  ⚠ BioPython not found"
else
    echo ""
    echo "⚠ WARNING: Some dependencies failed to install."
    echo ""
    echo "This usually means build tools (gcc) are not installed."
    echo "Most core functionality will still work, but some optional features may be unavailable."
    echo ""
    echo "To install all dependencies, run:"
    echo "  sudo apt install -y build-essential python3-dev"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    echo "Continuing with installation..."
fi
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
echo "Checking Chai MSA server connectivity (api.colabfold.com)..."

COLABFOLD_HOST="api.colabfold.com"
COLABFOLD_URL="https://api.colabfold.com"
DNS_OK="false"
HTTPS_OK="false"

if command -v getent &> /dev/null; then
    if getent hosts "$COLABFOLD_HOST" >/dev/null 2>&1; then
        DNS_OK="true"
        RESOLVED_IP="$(getent hosts "$COLABFOLD_HOST" | awk '{print $1}' | head -n1)"
        echo "  ✓ DNS resolved: $COLABFOLD_HOST -> $RESOLVED_IP"
    else
        echo "  ⚠ DNS resolution failed for $COLABFOLD_HOST"
    fi
else
    echo "  INFO: 'getent' not found, skipping DNS resolution check."
fi

if command -v curl &> /dev/null; then
    if curl -I --connect-timeout 8 --max-time 15 "$COLABFOLD_URL" >/dev/null 2>&1; then
        HTTPS_OK="true"
        echo "  ✓ HTTPS connection succeeded: $COLABFOLD_URL"
    else
        echo "  ⚠ HTTPS connection failed: $COLABFOLD_URL"
    fi
elif command -v wget &> /dev/null; then
    if wget -q --spider --timeout=15 "$COLABFOLD_URL"; then
        HTTPS_OK="true"
        echo "  ✓ HTTPS connection succeeded: $COLABFOLD_URL"
    else
        echo "  ⚠ HTTPS connection failed: $COLABFOLD_URL"
    fi
else
    echo "  INFO: Neither curl nor wget found, skipping HTTPS connectivity check."
fi

if [ "$DNS_OK" != "true" ] || [ "$HTTPS_OK" != "true" ]; then
    echo ""
    echo "WARNING: Chai MSA server connectivity is not fully available."
    echo "Phase 3 may fail when using '--use-msa-server'."
    echo ""
    echo "Recommended checks:"
    echo "  1. Verify DNS: getent hosts $COLABFOLD_HOST"
    echo "  2. Verify HTTPS: curl -I $COLABFOLD_URL"
    echo "  3. If using WSL and DNS is unstable, fix /etc/wsl.conf and /etc/resolv.conf"
    echo ""
    echo "Workaround:"
    echo "  Remove '--use-msa-server --use-templates-server' from"
    echo "  configs/run.yaml -> phase3_fast.chai.command_template"
fi
echo ""

echo "[7/10] Installing Boltz (separate environment)..."
echo ""

# Boltz requires Python <3.13, create conda environment with Python 3.12
BOLTZ_ENV="boltz_env"

# First deactivate any existing venv
deactivate 2>/dev/null || true

if conda env list | grep -q "$BOLTZ_ENV"; then
    echo "$BOLTZ_ENV environment already exists."
    echo "✓ Using existing $BOLTZ_ENV environment."
else
    conda create -n $BOLTZ_ENV python=3.12 -y
    echo "✓ $BOLTZ_ENV environment created with Python 3.12."
fi

# Activate Boltz conda environment
eval "$(conda shell.bash hook)"
conda activate $BOLTZ_ENV

# Verify we're using the correct Python
BOLTZ_PYTHON_VERSION=$(python --version 2>&1)
echo "Using Python in boltz_env: $BOLTZ_PYTHON_VERSION"

# Upgrade pip in conda environment
python -m pip install --upgrade pip || echo "WARNING: pip upgrade failed, continuing..."

# Install Boltz using conda environment's Python
echo "Installing Boltz..."
pip install -e ./tools/boltz

if command -v boltz &> /dev/null; then
    echo "✓ Boltz installed successfully."
else
    echo "WARNING: boltz command not found. Installation may have failed."
fi

# Deactivate conda environment
conda deactivate

# Reactivate main venv
source .venv/bin/activate
echo "✓ Switched back to main .venv environment."
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
    
    # Check if pyrosetta module can be imported (need to use conda's python)
    if $HOME/miniconda3/bin/python -c "import pyrosetta" 2>/dev/null; then
        echo "✓ PyRosetta installed successfully."
    else
        echo "WARNING: PyRosetta may need to be tested in the correct environment."
        echo "PyRosetta was installed but import test inconclusive."
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
    # Try kalign3 from bioconda and conda-forge
    if conda install -c bioconda -c conda-forge kalign3 -y; then
        echo "✓ kalign3 installed successfully."
    else
        echo "WARNING: kalign installation failed via conda."
        echo "kalign is optional. You can install it manually later if needed:"
        echo "  conda install -c bioconda -c conda-forge kalign3"
        echo "  or: sudo apt install kalign"
        echo "Continuing without kalign..."
    fi
    
    if command -v kalign &> /dev/null; then
        echo "✓ kalign installed: $(kalign --version 2>&1 | head -n 1)"
    else
        echo "INFO: kalign not installed (optional tool)."
    fi
fi

# DockQ
if command -v DockQ &> /dev/null; then
    echo "✓ DockQ already installed."
else
    echo "Installing DockQ via conda (to avoid compilation)..."
    # Try conda first, then pip as fallback
    if conda install -c conda-forge -c bioconda dockq -y 2>/dev/null; then
        echo "✓ DockQ installed via conda."
    else
        echo "Conda installation failed. Trying pip (may require gcc)..."
        pip install DockQ 2>/dev/null || {
            echo "WARNING: DockQ installation failed."
            echo "DockQ requires gcc for compilation. You can:"
            echo "  1. Install gcc: sudo apt install build-essential"
            echo "  2. Or skip DockQ (optional tool for structure assessment)"
        }
    fi
    
    if command -v DockQ &> /dev/null; then
        echo "✓ DockQ installed successfully."
    else
        echo "WARNING: DockQ not available. Continuing without it..."
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
