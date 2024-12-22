#!/bin/bash
# Copyright (c) 2024 texer.ai. All rights reserved.

set -euo pipefail

check_and_install() {
    if ! command -v ruff >/dev/null 2>&1; then
        echo "[WARNING] Missing package: Ruff"
        read -p "[PROMPT] Do you want to install it? [y/N] " response

        case "$response" in
            [Yy]*)
                echo "[INFO] Installing Ruff..."
                pip install ruff
                echo "[INFO] Package installed successfully."
                ;;
            *)
                echo "[ERROR] Cannot proceed without Ruff."
                exit 1
                ;;
        esac
    fi
}

echo "[INFO] Checking required packages..."
check_and_install

echo "[INFO] Formatting the project..."
ruff check --fix .
ruff format --line-length 160 .
echo "[INFO] Formatting complete."