#!/bin/sh
# Verify the packaged gdict plugin ELF and its public AbiWord plugin ABI.
set -eu

pkg_folder=${1:-}
if [ -z "$pkg_folder" ]; then
    echo "ERROR: package folder path is required" >&2
    exit 1
fi

plugin_dir="$pkg_folder/lib/abiword/plugins"
so=""
if [ -d "$plugin_dir" ]; then
    so=$(find "$plugin_dir" -maxdepth 1 \( -type f -o -type l \) -name 'gdict*.so*' | head -n 1)
fi
if [ -z "$so" ]; then
    so=$(find "$pkg_folder" \( -type f -o -type l \) -name 'gdict*.so*' | head -n 1)
fi
if [ -z "$so" ]; then
    echo "ERROR: gdict plugin .so not found" >&2
    exit 1
fi
echo "[ok] plugin: $so"

readelf_bin=""
for candidate in /data/service/hnp/bin/readelf /data/service/hnp/bin/llvm-readelf; do
    if [ -x "$candidate" ]; then
        readelf_bin="$candidate"
        break
    fi
done
if [ -z "$readelf_bin" ] && command -v readelf >/dev/null 2>&1; then
    readelf_bin=$(command -v readelf)
fi
if [ -z "$readelf_bin" ]; then
    echo "ERROR: readelf not found" >&2
    exit 1
fi

if ! "$readelf_bin" -h "$so" | grep -Eq 'Type:[[:space:]]+DYN'; then
    echo "ERROR: gdict plugin is not an ELF shared object" >&2
    exit 1
fi
echo "[ok] ELF type: DYN"

symbols=$($readelf_bin --dyn-syms -W "$so")
for symbol in abi_plugin_register abi_plugin_unregister abi_plugin_supports_version; do
    if ! printf '%s\n' "$symbols" | grep -q "$symbol"; then
        echo "ERROR: missing exported symbol: $symbol" >&2
        exit 1
    fi
    echo "[ok] exported symbol: $symbol"
done

echo "=== Results: 5 passed, 0 failed ==="
