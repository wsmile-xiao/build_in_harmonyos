#!/usr/bin/env sh
set -eu

NVIM_QT="${1:-nvim-qt}"
command -v "$NVIM_QT" >/dev/null 2>&1
version_output=$("$NVIM_QT" --version 2>&1)
echo "$version_output" | grep -q '0.2.19'
