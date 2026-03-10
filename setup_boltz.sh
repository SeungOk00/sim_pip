#!/bin/bash

set -e

echo "=========================================="
echo "Boltz Installation (Separate Environment)"
echo "=========================================="
echo ""

PROJECT_ROOT="/home01/hpc194a02/test/sim_pip"
cd "$PROJECT_ROOT"

echo "[1/3] Creating Boltz virtual environment..."
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
echo ""

echo "[2/3] Installing Boltz..."
echo ""

source .boltz_venv/bin/activate
pip install --upgrade pip
pip install -e ./tools/boltz
echo "✓ Boltz installed."
echo ""

echo "[3/3] Verifying installation..."
echo ""

if command -v boltz &> /dev/null; then
    echo "✓ Boltz command available."
    boltz --help | head -n 5
else
    echo "WARNING: boltz command not found."
fi

deactivate
echo ""

echo "=========================================="
echo "Boltz installation completed!"
echo "=========================================="
echo ""
echo "To use Boltz, make sure your config.py has:"
echo '  "boltz": {'
echo '    "enabled": True,'
echo '    "venv_path": "/home01/hpc194a02/test/sim_pip/.boltz_venv"'
echo '  }'
echo ""
echo "To test: source .boltz_venv/bin/activate && boltz --help"
echo ""
