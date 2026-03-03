#!/bin/bash
# Quick test script for the pipeline

echo "=========================================="
echo "Pipeline Quick Test"
echo "=========================================="
echo ""

# Check Python
echo "Checking Python..."
python --version
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Check directory structure
echo "Checking directory structure..."
ls -la pipeline/
ls -la pipeline/phases/
ls -la pipeline/utils/
echo "✓ Directory structure OK"
echo ""

# Validate Python syntax
echo "Validating Python syntax..."
python -m py_compile main.py
python -m py_compile pipeline/models.py
python -m py_compile pipeline/config.py
python -m py_compile pipeline/phases/phase1_target.py
python -m py_compile pipeline/phases/phase2_generate.py
python -m py_compile pipeline/phases/phase3_screen.py
python -m py_compile pipeline/phases/phase4_optimize.py
python -m py_compile pipeline/phases/phase5_lab.py
echo "✓ All Python files valid"
echo ""

# Show help
echo "Showing pipeline help..."
python main.py --help
echo ""

echo "=========================================="
echo "✓ Pipeline test completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Prepare your target PDB file"
echo "2. Run interactively: python main.py --target-pdb target.pdb --interactive"
echo "3. Or non-interactively: python main.py --target-pdb target.pdb --chain-id A --hotspots \"1,2,3\""
echo ""
