#!/usr/bin/env bash
set -euo pipefail

whichman_bin="${1:?missing whichman binary}"
ftff_bin="${2:?missing ftff binary}"
ftwhich_bin="${3:?missing ftwhich binary}"

for tool in "$whichman_bin" "$ftff_bin" "$ftwhich_bin"; do
    if [ ! -x "$tool" ]; then
        echo "missing or non-executable package binary: $tool" >&2
        exit 1
    fi
done

runner=()
case "$(uname -m)" in
    aarch64|arm64) ;;
    *)
        if ! qemu_aarch64="$(command -v qemu-aarch64)"; then
            echo "qemu-aarch64 is required to test the static AArch64 package on this runner" >&2
            exit 1
        fi
        runner=("$qemu_aarch64")
        ;;
esac

tmp_root="${TMPDIR:-$HOME/tmp}"
mkdir -p "$tmp_root"
work="$(mktemp -d "$tmp_root/whichman-test-XXXXXX")"
trap 'rm -rf "$work"' EXIT

mkdir -p "$work/man/man1"
: > "$work/man/man1/grep.1"

man_result="$(MANPATH="$work/man" "${runner[@]}" "$whichman_bin" -e grep)"
[ "$man_result" = "$work/man/man1/grep.1" ]
if MANPATH="$work/man" "${runner[@]}" "$whichman_bin" -e missing >/dev/null 2>&1; then
    echo "whichman unexpectedly found a missing man page" >&2
    exit 1
fi

mkdir -p "$work/path"
printf '#!/bin/sh\nexit 0\n' > "$work/path/helper"
chmod 755 "$work/path/helper"
ftwhich_result="$(PATH="$work/path" "${runner[@]}" "$ftwhich_bin" -0 helper)"
[ "$ftwhich_result" = "$work/path/helper" ]

mkdir -p "$work/tree/sub"
: > "$work/tree/note.txt"
ftff_result="$("${runner[@]}" "$ftff_bin" -0 "$work/tree" note.txt)"
[ "$ftff_result" = "$work/tree/note.txt" ]

echo "[ok] whichman, ftwhich, and ftff functional checks passed"
