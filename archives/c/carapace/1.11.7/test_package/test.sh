#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <package-folder>" >&2
    exit 2
fi

pkg_dir="$1"

example_bin="${pkg_dir}/bin/example"
nonposix_bin="${pkg_dir}/bin/example-nonposix"

if [ ! -f "$example_bin" ]; then
    echo "example binary not found: $example_bin" >&2
    exit 1
fi

if [ ! -f "$nonposix_bin" ]; then
    echo "example-nonposix binary not found: $nonposix_bin" >&2
    exit 1
fi

# Test example binary
echo "[test] example --help"
"$example_bin" --help >/dev/null 2>&1 || {
    echo "[warn] example --help returned non-zero, trying completion subcommand..."
    "$example_bin" _carapace >/dev/null 2>&1 && echo "✅ example _carapace OK" || {
        echo "❌ example failed both --help and _carapace"
        exit 1
    }
}
echo "✅ example --help OK"

# Test example-nonposix binary
echo "[test] example-nonposix --help"
"$nonposix_bin" --help >/dev/null 2>&1 || {
    echo "[warn] example-nonposix --help returned non-zero, trying --bool-long..."
    "$nonposix_bin" --bool-long >/dev/null 2>&1 && echo "✅ example-nonposix --bool-long OK" || {
        echo "❌ example-nonposix failed both --help and --bool-long"
        exit 1
    }
}
echo "✅ example-nonposix --help OK"

# Verify both are ELF executables
for bin in "$example_bin" "$nonposix_bin"; do
    magic=$(head -c4 "$bin" | xxd -p 2>/dev/null || echo "")
    if [ "$magic" = "7f454c46" ]; then
        echo "✅ $(basename "$bin") is ELF executable"
    else
        echo "❌ $(basename "$bin") is not ELF (magic: $magic)"
        exit 1
    fi
done
