#!/bin/sh
# Install script for iputils
# This script installs the latest version of iputils

LATEST_VERSION="20240905"
PREFIX="${PREFIX:-$HOME/usr/local}"

echo "Installing iputils $LATEST_VERSION to $PREFIX..."

cd "$(dirname "$0")/$LATEST_VERSION/packaging" || exit 1

if [ -f "iputils-$LATEST_VERSION-ohos-aarch64.tar.gz" ]; then
    mkdir -p "$PREFIX"
    tar xzf "iputils-$LATEST_VERSION-ohos-aarch64.tar.gz" -C "$PREFIX"
    echo ""
    echo "Installation complete!"
    echo "Installed tools:"
    echo "  - ping (IPv4/IPv6 unified)"
    echo "  - tracepath (IPv4/IPv6 unified)"
    echo "  - arping"
    echo "  - clockdiff"
    echo ""
    echo "Usage:"
    echo "  $PREFIX/bin/ping <host>        # IPv4 ping"
    echo "  $PREFIX/bin/ping ::1           # IPv6 ping"
    echo "  $PREFIX/bin/tracepath <host>   # IPv4 tracepath"
    echo "  $PREFIX/bin/tracepath ::1      # IPv6 tracepath"
else
    echo "Error: Package file not found"
    exit 1
fi
