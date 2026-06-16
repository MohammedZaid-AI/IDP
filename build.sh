#!/usr/bin/env bash
# Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Create data directories (persistent disk on Render, local otherwise)
mkdir -p uploads exports
