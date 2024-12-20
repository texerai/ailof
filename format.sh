#!/bin/bash
# Copyright (c) 2024 texer.ai. All rights reserved.

set -euo pipefail

check_and_install() {
    local missing=()
    
    if ! command -v isort >/dev/null 2>&1; then
        missing+=("isort")
    fi
    
    if ! command -v black >/dev/null 2>&1; then
        missing+=("black")
    fi
    
    if [ ${#missing[@]} -eq 0 ]; then
        return 0
    fi

    echo "[WARNING] Missing packages: ${missing[*]}"
    read -p "[PROMPT] Do you want to install them? [y/N] " response

    case "$response" in
        [Yy]*)
            echo "[INFO] Installing missing packages..."
            pip install "${missing[@]}"
            echo "[INFO] Packages installed successfully."
            ;;
        *)
            echo "[ERROR] Cannot proceed without required packages."
            exit 1
            ;;
    esac
}

echo "[INFO] Checking required packages..."
check_and_install

echo "[INFO] Formatting the project..."
isort --profile black -l 160 .
black -l 160 .
echo "[INFO] Formatting complete."
