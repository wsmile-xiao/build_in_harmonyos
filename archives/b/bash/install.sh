#!/bin/sh
# Install script for bash (OpenHarmony)
# Usage: curl -fsSL <url>/install.sh | sh -s -- [version]
set -e
PREFIX="${HOME}/usr/local"
VERSION="${1:-5.3}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="${SCRIPT_DIR}/${VERSION}/packaging"

if [ ! -f "${PKG_DIR}/bash-${VERSION}-ohos-aarch64.tar.gz" ]; then
    echo "Error: bash ${VERSION} package not found"
    exit 1
fi

TMPDIR="${TMPDIR:-$HOME/tmp}"
EXTRACT_DIR="${TMPDIR}/bash-${VERSION}-install"
rm -rf "${EXTRACT_DIR}"
mkdir -p "${EXTRACT_DIR}"

tar xzf "${PKG_DIR}/bash-${VERSION}-ohos-aarch64.tar.gz" -C "${EXTRACT_DIR}"

for d in bin lib include share; do
    [ -d "${EXTRACT_DIR}/$d" ] && cp -a "${EXTRACT_DIR}/$d/" "${PREFIX}/$d/"
done

chmod +x "${PREFIX}/bin/"* 2>/dev/null || true
rm -rf "${EXTRACT_DIR}"

echo "bash ${VERSION} installed to ${PREFIX}"
