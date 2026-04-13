#!/bin/sh
# htop 3.4.1 installer for OpenHarmony
# Usage: sh install.sh [PREFIX]
set -e
PREFIX="${1:-$HOME/usr/local}"
TMPDIR="${TMPDIR:-$HOME/tmp}"

# Copy files
cp -r bin share "$PREFIX/"

# Ensure binary is executable
chmod +x "$PREFIX/bin/htop"

echo "✅ htop 3.4.1 installed to $PREFIX"
echo "   Run: sudo $PREFIX/bin/htop"
echo "   Note: htop requires sudo to access /proc on HarmonyOS"
