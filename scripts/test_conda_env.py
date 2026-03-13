#!/usr/bin/env python3
"""
Quick test to verify RFdiffusion uses correct conda environment
"""
import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_conda_python_detection():
    """Test that RFdiffusionRunner can find conda Python"""
    from pipeline.utils.tool_wrapper import RFdiffusionRunner
    
    logger.info("=" * 80)
    logger.info("Testing conda Python detection")
    logger.info("=" * 80)
    
    runner = RFdiffusionRunner(
        tool_path=str(project_root / 'tools' / 'rfdiffusion'),
        conda_env='SE3nv'
    )
    
    conda_python = runner._get_conda_python()
    
    if conda_python:
        logger.info(f"✓ Found conda Python: {conda_python}")
        
        # Verify it's the right Python
        import subprocess
        result = subprocess.run([conda_python, '--version'], 
                              capture_output=True, text=True, timeout=5)
        logger.info(f"  Version: {result.stdout.strip()}")
        
        # Test dgl import
        result = subprocess.run(
            [conda_python, '-c', 'import dgl; print("dgl OK")'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            logger.info(f"  ✓ dgl import: {result.stdout.strip()}")
        else:
            logger.error(f"  ✗ dgl import failed: {result.stderr}")
            return False
        
        return True
    else:
        logger.error("✗ Could not find conda Python")
        return False

def test_environment_isolation():
    """Test that VIRTUAL_ENV is properly isolated"""
    import os
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("Testing environment isolation")
    logger.info("=" * 80)
    
    logger.info(f"Current Python: {sys.executable}")
    logger.info(f"VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', 'Not set')}")
    logger.info(f"PYTHONHOME: {os.environ.get('PYTHONHOME', 'Not set')}")
    
    # Test that .venv can't import dgl (should fail with Python 3.13)
    try:
        import dgl
        logger.warning("⚠ dgl imported in .venv (unexpected!)")
        return False
    except ImportError as e:
        logger.info(f"✓ dgl correctly fails to import in .venv: {str(e)[:80]}")
        return True

def main():
    logger.info("RFdiffusion Environment Test")
    logger.info("=" * 80)
    
    test1 = test_conda_python_detection()
    test2 = test_environment_isolation()
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Conda Python detection: {'✓ PASS' if test1 else '✗ FAIL'}")
    logger.info(f"Environment isolation: {'✓ PASS' if test2 else '✗ FAIL'}")
    
    if test1 and test2:
        logger.info("")
        logger.info("✓ All tests passed! RFdiffusion should use SE3nv conda environment.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run: python scripts/test_phase1_2_3.py")
        logger.info("  2. Check logs for: 'Found conda Python at: ...'")
        logger.info("  3. Verify no more '.venv/lib/python3.13/site-packages/dgl' errors")
        return 0
    else:
        logger.error("")
        logger.error("✗ Some tests failed. Check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
