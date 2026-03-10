#!/bin/bash

set -e

echo "=========================================="
echo "PyRosetta Installation Options"
echo "=========================================="
echo ""

PROJECT_ROOT="/home01/hpc194a02/test/sim_pip"
cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
    echo "ERROR: .venv not found. Please run setup.sh first."
    exit 1
fi

source .venv/bin/activate

echo "PyRosetta Installation Options:"
echo ""
echo "1. Standard Release (default)"
echo "2. Release with distributed support"
echo "3. Release with serialization support"
echo "4. MinSizeRel build"
echo "5. Custom installation"
echo ""

read -p "Select option (1-5) [1]: " OPTION
OPTION=${OPTION:-1}

echo ""
echo "Installing pyrosetta-installer..."
pip install pyrosetta-installer

echo ""
echo "Installing PyRosetta (this may take several minutes)..."
echo ""

case $OPTION in
    1)
        echo "Installing standard Release build..."
        python -c 'import pyrosetta_installer; pyrosetta_installer.install_pyrosetta()'
        ;;
    2)
        echo "Installing Release with distributed support..."
        python -c 'import pyrosetta_installer; pyrosetta_installer.install_pyrosetta(distributed=True)'
        ;;
    3)
        echo "Installing Release with serialization support..."
        python -c 'import pyrosetta_installer; pyrosetta_installer.install_pyrosetta(serialization=True)'
        ;;
    4)
        echo "Installing MinSizeRel build..."
        python -c "import pyrosetta_installer; pyrosetta_installer.install_pyrosetta(type='MinSizeRel')"
        ;;
    5)
        echo "Custom installation:"
        echo ""
        read -p "Install distributed support? (y/n) [n]: " DISTRIBUTED
        read -p "Install serialization support? (y/n) [n]: " SERIALIZATION
        read -p "Build type (Release/MinSizeRel) [Release]: " BUILD_TYPE
        read -p "Mirror (0=west, 1=east) [0]: " MIRROR
        
        DISTRIBUTED=${DISTRIBUTED:-n}
        SERIALIZATION=${SERIALIZATION:-n}
        BUILD_TYPE=${BUILD_TYPE:-Release}
        MIRROR=${MIRROR:-0}
        
        DIST_FLAG="False"
        [[ $DISTRIBUTED =~ ^[Yy]$ ]] && DIST_FLAG="True"
        
        SERIAL_FLAG="False"
        [[ $SERIALIZATION =~ ^[Yy]$ ]] && SERIAL_FLAG="True"
        
        echo ""
        echo "Installing with custom options:"
        echo "  distributed=$DIST_FLAG"
        echo "  serialization=$SERIAL_FLAG"
        echo "  type='$BUILD_TYPE'"
        echo "  mirror=$MIRROR"
        echo ""
        
        python -c "import pyrosetta_installer; pyrosetta_installer.install_pyrosetta(distributed=$DIST_FLAG, serialization=$SERIAL_FLAG, type='$BUILD_TYPE', mirror=$MIRROR)"
        ;;
    *)
        echo "Invalid option. Installing standard Release build..."
        python -c 'import pyrosetta_installer; pyrosetta_installer.install_pyrosetta()'
        ;;
esac

echo ""
echo "Verifying installation..."
if python -c "import pyrosetta" 2>/dev/null; then
    echo ""
    echo "✓ PyRosetta installed successfully!"
    echo ""
    python -c "import pyrosetta; print(f'PyRosetta version: {pyrosetta.__version__}')" 2>/dev/null || echo "PyRosetta is ready to use."
else
    echo ""
    echo "✗ PyRosetta installation failed."
    echo ""
    echo "Troubleshooting:"
    echo "1. Try again with a different build type"
    echo "2. Check your internet connection"
    echo "3. Try using setup.py package instead of wheel:"
    echo "   python -c 'import pyrosetta_installer; pyrosetta_installer.install_pyrosetta(use_setup_py_package=True)'"
    exit 1
fi

echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
echo ""
echo "Note: The installer uses 'devel' (weekly) builds."
echo "These are not kept indefinitely and may not be suitable"
echo "for long-term reproducible results."
echo ""
echo "For more options, see:"
echo "  https://pypi.org/project/pyrosetta-installer"
echo ""
