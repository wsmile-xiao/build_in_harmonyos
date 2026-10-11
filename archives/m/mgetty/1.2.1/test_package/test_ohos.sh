#!/usr/bin/env bash
# HarmonyOS-specific test for mgetty 1.2.1.
#
# Checks the installed artefacts against the OHOS target (aarch64-linux-ohos,
# musl + libc++): the compiled tools must be ELF64/AArch64 executables with no
# Linux-only shared-library dependencies (the upstream Linux default links
# -lutil, which the recipe removes), the generated front-end scripts must be
# installed executable with a valid shebang, and the G3 pipeline must be
# byte-deterministic when run on the device (mirrors the upstream expectation).
set -u
BIN="$1"
READELF="${READELF:-llvm-readelf}"
fails=0

ok()   { echo "ok   - $1"; }
fail() { echo "FAIL - $1" >&2; fails=$((fails + 1)); }

# Compiled tools (ELF) vs. sedscript-generated front-ends (shell/perl).
elf_bins="mgetty sendfax newslock g3cat g32pbm pbm2g3 sff2g3 faxq-helper"
script_bins="faxspool faxrunq faxq faxrm faxrunqd"

# 1) compiled tools are ELF64 / AArch64 objects
for b in $elf_bins; do
    hdr="$("$READELF" -h "$BIN/$b" 2>/dev/null)"
    if echo "$hdr" | grep -q "ELF64" && echo "$hdr" | grep -q "AArch64"; then
        ok "$b is ELF64/AArch64"
    else
        fail "$b is not an ELF64/AArch64 object"
    fi
done

# 2) generated front-ends are executable and carry a shebang
for b in $script_bins; do
    first="$(head -n 1 "$BIN/$b" 2>/dev/null)"
    if [ -x "$BIN/$b" ] && [ "${first#\#!}" != "$first" ]; then
        ok "$b is an executable script ($(echo "$first" | cut -c1-24))"
    else
        fail "$b is not an executable script"
    fi
done

# 3) no Linux-only shared-library dependencies in the compiled tools
linux_only=""
for b in $elf_bins; do
    if "$READELF" -d "$BIN/$b" 2>/dev/null | grep -qE "libutil|libpthread|librt\.so"; then
        linux_only="$linux_only $b"
    fi
done
if [ -z "$linux_only" ]; then
    ok "no Linux-only dynamic dependencies across the compiled tools"
else
    fail "Linux-only NEEDED entries in:$linux_only"
fi

# 4) the tools actually execute on OHOS and the G3 pipeline is deterministic
if "$BIN/g3cat" -h 2>&1 | grep -qi usage; then ok "g3cat executes on OHOS"; else fail "g3cat did not run on OHOS"; fi

tmp="$(mktemp -d "${TMPDIR:-/tmp}/mgetty-ohos.XXXXXX")" || { echo "FAIL: mktemp" >&2; exit 1; }
trap 'rm -rf "$tmp"' EXIT
cd "$tmp" || exit 1
printf 'P1 1 10\n0 0 0 0 0 0 0 0 0 0\n' | "$BIN/pbm2g3" > t.g3
n="$("$BIN/g3cat" -p 100 -a -R t.g3 | wc -c | tr -d ' ')"
if [ "$n" = "1002" ]; then ok "G3 padding deterministic on OHOS (1002 B)"; else fail "G3 padding on OHOS: got $n, expected 1002"; fi

if [ "$fails" -ne 0 ]; then
    echo "$fails HarmonyOS assertion(s) failed" >&2
    exit 1
fi
echo "all mgetty HarmonyOS assertions passed"
