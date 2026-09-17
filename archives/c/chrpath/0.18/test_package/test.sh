#!/bin/sh
set -eu

command -v chrpath >/dev/null 2>&1
chrpath --version | grep -F '0.18' >/dev/null
chrpath --help >/dev/null

probe=""
if [ -n "${CHRPATH_PROBE:-}" ] && [ -f "${CHRPATH_PROBE}" ]; then
    probe=${CHRPATH_PROBE}
else
    probe=$(find . -type f -name chrpath_rpath_probe -print -quit)
fi
if [ -z "${probe}" ] || [ ! -f "${probe}" ]; then
    echo "chrpath_rpath_probe was not built" >&2
    exit 1
fi

chrpath --list "${probe}" | grep -F '/data/local/tmp/chrpath-ohos-old' >/dev/null
chrpath --replace /data/local/tmp/chrpath-new "${probe}"
chrpath --list "${probe}" | grep -F '/data/local/tmp/chrpath-new' >/dev/null

if chrpath --delete "${probe}"; then
    if chrpath --list "${probe}" >/dev/null 2>&1; then
        echo "chrpath --delete left an RPATH/RUNPATH entry" >&2
        exit 1
    fi
else
    echo "chrpath --delete failed" >&2
    exit 1
fi

tmp_root=${TMPDIR:-${HOME:-.}/tmp}
mkdir -p "${tmp_root}"
not_elf="${tmp_root}/chrpath-not-elf.$$"
trap 'rm -f "${not_elf}"' EXIT
printf 'not an ELF file\n' > "${not_elf}"
if chrpath "${not_elf}" >/dev/null 2>&1; then
    echo "chrpath accepted a non-ELF input" >&2
    exit 1
fi

echo "chrpath consumer test passed"
