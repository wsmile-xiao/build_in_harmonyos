#!/bin/sh
# test_package/test_bosixnet.sh — 验证 bosixnet_webui 二进制功能正常
set -eu

# Smoke test for the packaged bosixnet_webui FastCGI binary:
# `bosixnet_webui --version` prints the version banner and exits 0.
# This file satisfies CI L0c: test source file requirement; the authoritative
# run is performed by conanfile.py's test() method.

webui="${1:-bosixnet_webui}"

if "$webui" --version >/dev/null 2>&1; then
    echo "        [ok] bosixnet_webui --version exits 0"
else
    echo "        [fail] bosixnet_webui --version failed"
    exit 1
fi