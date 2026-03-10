#!/bin/bash

# Cleanup script for misplaced outputs folder

PROJECT_ROOT="/home01/hpc194a02/test/sim_pip"

echo "=========================================="
echo "Cleanup Misplaced Outputs Folder"
echo "=========================================="
echo ""

if [ -d "$PROJECT_ROOT/outputs" ]; then
    echo "Found misplaced outputs folder at: $PROJECT_ROOT/outputs"
    echo ""
    echo "Contents:"
    ls -lh "$PROJECT_ROOT/outputs"
    echo ""
    
    read -p "Do you want to delete this folder? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Deleting $PROJECT_ROOT/outputs..."
        rm -rf "$PROJECT_ROOT/outputs"
        echo "✓ Deleted."
    else
        echo "Skipped deletion."
    fi
else
    echo "✓ No misplaced outputs folder found."
fi

echo ""
echo "Note: Outputs should be stored in data/outputs/"
echo ""
