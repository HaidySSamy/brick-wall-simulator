#!/usr/bin/env bash
set -euo pipefail

echo "┌──────────────────────────────────────────────┐"
echo "│  Masonry‐Wall‐Simulator: Install Script     │"
echo "└──────────────────────────────────────────────┘"
echo

# Detect platform
OSTYPE=$(uname | tr '[:upper:]' '[:lower:]')

# ── 1) Ensure python3 is installed ───────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "NOTICE: python3 not found."
  if [[ "$OSTYPE" == *"linux"* ]]; then
    echo "Attempting to install python3 via system package manager..."
    if command -v apt-get &>/dev/null; then
      sudo apt-get update
      sudo apt-get install -y python3 python3-pip
    elif command -v yum &>/dev/null; then
      sudo yum install -y python3 python3-pip
    else
      echo "ERROR: No compatible package manager found (apt-get or yum)."
      echo "Please install Python 3 manually."
      exit 1
    fi
  elif [[ "$OSTYPE" == *"darwin"* ]]; then
    echo "Attempting to install python3 via Homebrew..."
    if command -v brew &>/dev/null; then
      brew update
      brew install python
    else
      echo "ERROR: Homebrew not found. Please install Homebrew or Python 3 manually."
      exit 1
    fi
  else
    echo "ERROR: Unsupported OS or cannot auto‐install python3."
    echo "Please install Python 3 (>=3.7) manually."
    exit 1
  fi
else
  echo "python3 is already installed."
fi

# Refresh PATH if python3 was just installed
export PATH="$(python3 -c 'import sys; print(sys.executable[:sys.executable.rfind("/")])'):$PATH"

# ── 2) Ensure pip3 is installed ─────────────────────────────────────────────────
if ! command -v pip3 &>/dev/null; then
  echo "pip3 not found; attempting to use python3 -m ensurepip..."
  python3 -m ensurepip --upgrade || true
  if ! command -v pip3 &>/dev/null; then
    echo "ERROR: pip3 still not available. Please install pip for Python 3 manually."
    exit 1
  fi
else
  echo "pip3 is already installed."
fi

# ── 3) Upgrade pip ───────────────────────────────────────────────────────────────
echo "→ Upgrading pip..."
pip3 install --upgrade pip

# ── 4) Install required packages ─────────────────────────────────────────────────
echo "→ Installing pygame via pip3..."
pip3 install pygame

echo
echo "✅ Dependencies installed successfully!"
echo
echo "To run the program:"
echo
echo "  python3 gui_wall_visualizer.py"
echo
echo "(On Windows, use 'python' instead of 'python3'.)"
echo

exit 0