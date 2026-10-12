#!/usr/bin/env bash
# test_package/test.sh - offline assertions against the packaged ktea binary.
# 5 checks total: existence, ELF magic, `ktea --help` usage text, and (--ohos
# only) OHOS ELF signature section + static linking. No network access.
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: $0 <path-to-ktea> [--ohos]" >&2
    exit 2
fi

ktea_bin="$1"
ohos_mode="false"
if [ "${2:-}" = "--ohos" ]; then
    ohos_mode="true"
fi

# 1. file existence + executable
if [ ! -x "$ktea_bin" ]; then
    echo "ktea binary not found or not executable: $ktea_bin" >&2
    exit 1
fi
echo "CHECK-OK: ktea binary exists and is executable"

# 2. ELF magic (\x7fELF)
if [ "$(head -c4 "$ktea_bin" | od -An -tx1 | tr -d ' \n')" != "7f454c46" ]; then
    echo "ktea is not an ELF binary" >&2
    exit 1
fi
echo "CHECK-OK: ktea binary has ELF magic"

# 3. `ktea --help` runs and prints the usage text mentioning the real flags
#    (-debug / -plain-fonts). ktea has no --version flag; Go's flag package
#    prints usage for -help/-h and exits 0.
help_output="$("$ktea_bin" --help 2>&1)"
if ! printf '%s\n' "$help_output" | grep -q -e "plain-fonts" -e "debug"; then
    echo "--help output did not mention plain-fonts/debug flags" >&2
    printf '%s\n' "$help_output" >&2
    exit 1
fi
echo "CHECK-OK: ktea --help prints usage with plain-fonts/debug flags"

if [ "$ohos_mode" = "true" ]; then
    # 4. OHOS adaptation point: binary carries the mandatory OHOS ELF
    #    signature section added by binary-sign-tool (unsigned ELF is
    #    refused by execve on HarmonyOS). Detected via readelf section table
    #    (robust; avoids scanning the 16MB binary as one text line).
    readelf_bin=""
    for candidate in readelf llvm-readelf; do
        if command -v "$candidate" >/dev/null 2>&1; then
            readelf_bin="$candidate"
            break
        fi
    done
    if [ -z "$readelf_bin" ]; then
        echo "no readelf/llvm-readelf on PATH for signature-section check" >&2
        exit 1
    fi
    if "$readelf_bin" -S "$ktea_bin" 2>/dev/null | grep -q -E "\\.codesign|\\.note\\.ohos"; then
        echo "CHECK-OK: binary carries OHOS signature section"
    else
        echo "binary lacks OHOS signature section (.codesign/.note.ohos)" >&2
        echo "readelf -S output (signature probe):" >&2
        "$readelf_bin" -S "$ktea_bin" 2>&1 | head -30 >&2
        exit 1
    fi

    # 5. OHOS adaptation point: CGO_ENABLED=0 build is statically linked -
    #    no PT_INTERP and no DT_NEEDED, i.e. no glibc/musl dynamic coupling.
    readelf_bin=""
    for candidate in readelf llvm-readelf; do
        if command -v "$candidate" >/dev/null 2>&1; then
            readelf_bin="$candidate"
            break
        fi
    done
    if [ -z "$readelf_bin" ]; then
        echo "no readelf/llvm-readelf on PATH for static-linking check" >&2
        exit 1
    fi
    if "$readelf_bin" -l "$ktea_bin" | grep -q "INTERP"; then
        echo "binary has PT_INTERP - not statically linked" >&2
        exit 1
    fi
    if "$readelf_bin" -d "$ktea_bin" | grep -q "NEEDED"; then
        echo "binary has DT_NEEDED entries - not statically linked" >&2
        exit 1
    fi
    echo "CHECK-OK: binary is statically linked (no PT_INTERP, no DT_NEEDED)"
    echo "All 5 ktea test_package checks passed."
else
    echo "All 3 ktea test_package checks passed."
fi
