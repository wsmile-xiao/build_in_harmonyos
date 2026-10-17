#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for the its-playback-time binaries.
#
# Runs inside the conanrun env (the packaged bin/ is on PATH and TERMINFO
# points at the packaged ncurses terminfo database).
#
# The two installed programs are:
#   ipbt       - the interactive curses player (needs a real terminal)
#   ipbt-dump  - the non-interactive converter (hex dump / typescript / XML)
#
# ipbt-dump is not a stub: it runs the same ipbtsrc/read.c ttyrec parser and
# the same PuTTY terminal emulator (terminal.c) as the player, so the
# functional tests below really do drive the ttyrec reader, the VT parser and
# the frame store. No assertion needs a curses initialisation, so everything
# runs headlessly.
#
# Assertions (14):
#   1  ipbt --version        prints exactly "ipbt, source commit <sha>"
#   2  ipbt --help           usage text lists the documented options
#   3  ipbt --licence        prints the MIT licence text
#   4  ipbt-dump --version   prints exactly "ipbt, source commit <sha>"
#   5  ipbt-dump --help      usage text lists -S/--script and -H/--hex-dump
#   6  ipbt-dump --licence   prints the MIT licence text
#   7  ipbt-dump -T          default SUMMARY mode frames the recording
#   8  ipbt-dump -T -S       typescript round-trip is byte-identical
#   9  ipbt-dump -T -H       hex dump shows the frame bytes and their ASCII
#  10  ipbt-dump -T -x       screen XML contains the emulated screen text
#  11  ipbt-dump -R -S       raw-byte mode round-trips a plain text file
#  12  error paths           no filename / missing file / bad option all fail
#  13  no-false-positive     a tampered payload must change the hex dump
#  14  format autodetect     the same file parses without an explicit -T
set -euo pipefail

# stdout only.  Every output compared below is stdout (--version / --help /
# --licence / SUMMARY / hex dump / screen XML -- verified by splitting the two
# streams by hand), so capture with `2>/dev/null` instead of `2>&1`.
# Reason not to fold stderr in: under WSL binfmt_misc the aarch64 guest runs
# through the x86_64 `qemu-binfmt` wrapper, which inherits LD_PRELOAD; its
# x86_64 ld.so cannot map the aarch64 guest fortify shim (ipbt needs
# __fd_chk) and writes one `... from LD_PRELOAD cannot be preloaded ...` line
# into the guest's stderr.  With `2>&1` that line becomes part of ${OUT} and
# breaks the two exact string compares below while the program itself printed
# exactly the right thing.  Do not "fix" this back.

PLAYER="${1:?usage: test.sh /path/to/ipbt /path/to/ipbt-dump}"
DUMPER="${2:?usage: test.sh /path/to/ipbt /path/to/ipbt-dump}"
PLAYER="$(readlink -f "${PLAYER}")"
DUMPER="$(readlink -f "${DUMPER}")"

# cmake/gitcommit.cmake bakes the upstream git commit into cmake_commit.c, and
# ipbtsrc/common.c reports it because PACKAGE_VERSION is only visible in
# unix/ipbt.c, not in the translation unit that prints the version.
EXPECTED_COMMIT="fdcd2b0ad60f74ffa6a695c992d56c6a3ae20e4a"
EXPECTED_VERSION="ipbt, source commit ${EXPECTED_COMMIT}"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/ipbt-test.XXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# ------------------------------------------------------------------ 1
echo "[1/14] ipbt --version"
OUT="$("${PLAYER}" --version 2>/dev/null)" || fail "ipbt --version exited non-zero"
[ "${OUT}" = "${EXPECTED_VERSION}" ] || \
    fail "ipbt --version printed [${OUT}], expected [${EXPECTED_VERSION}]"
echo "PASS: ${OUT}"

# ------------------------------------------------------------------ 2
echo "[2/14] ipbt --help"
OUT="$("${PLAYER}" --help 2>/dev/null)" || fail "ipbt --help exited non-zero"
echo "${OUT}" | grep -q 'usage: ipbt' || fail "ipbt --help lacks the usage banner"
echo "${OUT}" | grep -q -- '--utf8-linedraw' || fail "ipbt --help lacks --utf8-linedraw"
echo "${OUT}" | grep -q -- '-A          automatically start playing' || \
    fail "ipbt --help lacks the documented -A option"
echo "${OUT}" | grep -q -- '-f frame' || fail "ipbt --help lacks the documented -f option"
echo "PASS: usage text lists the documented options"

# ------------------------------------------------------------------ 3
echo "[3/14] ipbt --licence"
OUT="$("${PLAYER}" --licence 2>/dev/null)" || fail "ipbt --licence exited non-zero"
echo "${OUT}" | grep -q 'derived from the PuTTY source base' || \
    fail "ipbt --licence did not print the PuTTY copyright notice"
echo "${OUT}" | grep -q 'Permission is hereby granted, free of charge' || \
    fail "ipbt --licence did not print the MIT permission notice"
echo "PASS: MIT licence text printed"

# ------------------------------------------------------------------ 4
echo "[4/14] ipbt-dump --version"
OUT="$("${DUMPER}" --version 2>/dev/null)" || fail "ipbt-dump --version exited non-zero"
[ "${OUT}" = "${EXPECTED_VERSION}" ] || \
    fail "ipbt-dump --version printed [${OUT}], expected [${EXPECTED_VERSION}]"
echo "PASS: ${OUT}"

# ------------------------------------------------------------------ 5
echo "[5/14] ipbt-dump --help"
OUT="$("${DUMPER}" --help 2>/dev/null)" || fail "ipbt-dump --help exited non-zero"
echo "${OUT}" | grep -q 'usage:   ipbt-dump' || fail "ipbt-dump --help lacks the usage banner"
echo "${OUT}" | grep -q -- '-S, --script' || fail "ipbt-dump --help lacks -S, --script"
echo "${OUT}" | grep -q -- '-H, --hex-dump' || fail "ipbt-dump --help lacks -H, --hex-dump"
echo "${OUT}" | grep -q -- '-x, --screen-xml' || fail "ipbt-dump --help lacks -x, --screen-xml"
echo "PASS: usage text lists the dump output modes"

# ------------------------------------------------------------------ 6
echo "[6/14] ipbt-dump --licence"
OUT="$("${DUMPER}" --licence 2>/dev/null)" || fail "ipbt-dump --licence exited non-zero"
echo "${OUT}" | grep -q 'derived from the PuTTY source base' || \
    fail "ipbt-dump --licence did not print the PuTTY copyright notice"
echo "${OUT}" | grep -q 'Permission is hereby granted, free of charge' || \
    fail "ipbt-dump --licence did not print the MIT permission notice"
echo "PASS: MIT licence text printed"

# ------------------------------------------------------------------ fixture
# A minimal, valid ttyrec file: one frame at timestamp 0.000000 carrying 12
# bytes of raw terminal data ("hello ipbt\r\n").  The ttyrec header is three
# little-endian uint32 words: seconds, microseconds, data length.
printf 'hello ipbt\r\n' > "${WORK}/expected.bin"
printf '\000\000\000\000\000\000\000\000\014\000\000\000hello ipbt\r\n' \
    > "${WORK}/demo.ttyrec"
REC="${WORK}/demo.ttyrec"
[ "$(wc -c < "${REC}")" = "24" ] || fail "ttyrec fixture is not 12-byte header + 12 bytes of data"

# ------------------------------------------------------------------ 7
echo "[7/14] ipbt-dump -T (default SUMMARY mode)"
OUT="$("${DUMPER}" -T "${REC}" 2>/dev/null)" || fail "ipbt-dump -T exited non-zero"
echo "${OUT}"
echo "${OUT}" | grep -q ':0:0\.000000:offset 0xc len 0xc' || \
    fail "SUMMARY output does not describe frame 0 at 0.000000s with len 0xc (got [${OUT}])"
echo "PASS: frame summary parsed from the ttyrec header"

# ------------------------------------------------------------------ 8
echo "[8/14] ipbt-dump -T -S (typescript round-trip)"
"${DUMPER}" -T -S -o "${WORK}/out.script" "${REC}" || fail "ipbt-dump -T -S exited non-zero"
cmp -s "${WORK}/out.script" "${WORK}/expected.bin" || \
    fail "typescript output differs from the recorded terminal data"
echo "PASS: typescript output is byte-identical to the recorded data"

# ------------------------------------------------------------------ 9
echo "[9/14] ipbt-dump -T -H (hex dump)"
OUT="$("${DUMPER}" -T -H "${REC}" 2>/dev/null)" || fail "ipbt-dump -T -H exited non-zero"
echo "${OUT}"
echo "${OUT}" | grep -q '68 65 6c 6c 6f' || \
    fail "hex dump does not contain the bytes of \"hello\" (got [${OUT}])"
echo "${OUT}" | grep -q 'hello ipbt' || \
    fail "hex dump ASCII column does not show \"hello ipbt\" (got [${OUT}])"
echo "PASS: hex dump shows frame bytes and their ASCII rendering"

# ----------------------------------------------------------------- 10
echo "[10/14] ipbt-dump -T -x (screen XML via the terminal emulator)"
OUT="$("${DUMPER}" -T -x "${REC}" 2>/dev/null)" || fail "ipbt-dump -T -x exited non-zero"
echo "${OUT}" | grep -q '<ttyrecording' || fail "screen XML has no <ttyrecording> root"
echo "${OUT}" | grep -q '<frame index="0"' || fail "screen XML has no frame 0 element"
echo "${OUT}" | grep -q '<t>hello ipbt' || \
    fail "screen XML does not contain the emulated screen text \"hello ipbt\" (got [${OUT}])"
echo "${OUT}" | grep -q '</ttyrecording>' || fail "screen XML is not terminated"
echo "PASS: terminal emulator rendered the recorded text into XML"

# ----------------------------------------------------------------- 11
echo "[11/14] ipbt-dump -R -S (raw-byte mode)"
printf 'raw terminal bytes\n' > "${WORK}/raw.txt"
"${DUMPER}" -R -S -o "${WORK}/raw.out" "${WORK}/raw.txt" || \
    fail "ipbt-dump -R -S exited non-zero"
cmp -s "${WORK}/raw.out" "${WORK}/raw.txt" || \
    fail "raw-byte mode did not round-trip the input file"
echo "PASS: raw-byte mode round-tripped a plain text file"

# ----------------------------------------------------------------- 12
echo "[12/14] error paths"
set +e
"${DUMPER}" >/dev/null 2>&1; RC_NOFILE=$?
"${DUMPER}" -T "${WORK}/does-not-exist.ttyrec" >/dev/null 2>&1; RC_MISSING=$?
"${PLAYER}" --no-such-option >/dev/null 2>&1; RC_BADOPT=$?
set -e
[ "${RC_NOFILE}" -ne 0 ] || fail "ipbt-dump with no filename exited 0"
[ "${RC_MISSING}" -ne 0 ] || fail "ipbt-dump with a missing input file exited 0"
[ "${RC_BADOPT}" -ne 0 ] || fail "ipbt accepted an unknown long option"
echo "PASS: no-filename=${RC_NOFILE} missing-file=${RC_MISSING} bad-option=${RC_BADOPT} all non-zero"

# ----------------------------------------------------------------- 13
echo "[13/14] the fixture actually reached the parser"
# Guard against a vacuous pass: tampering with the recorded payload must change
# what the hex-dump path reports, proving the bytes were really read.
printf '\000\000\000\000\000\000\000\000\014\000\000\000hello ipqT\r\n' \
    > "${WORK}/tampered.ttyrec"
OUT_OK="$("${DUMPER}" -T -H "${REC}" 2>/dev/null)"
OUT_BAD="$("${DUMPER}" -T -H "${WORK}/tampered.ttyrec" 2>/dev/null)"
[ "${OUT_OK}" != "${OUT_BAD}" ] || \
    fail "hex dump is identical for different payloads - the parser is not reading the file"
echo "PASS: different payloads produce different dumps"

# ----------------------------------------------------------------- 14
echo "[14/14] ttyrec format autodetection (no explicit -T)"
OUT="$("${DUMPER}" -H "${REC}" 2>/dev/null)" || fail "ipbt-dump -H exited non-zero"
echo "${OUT}" | grep -q 'assuming ttyrec' || \
    fail "autodetection did not settle on the ttyrec format (got [${OUT}])"
echo "${OUT}" | grep -q ':0:0\.000000:offset 0xc len 0xc' || \
    fail "autodetected run did not report frame 0 (got [${OUT}])"
echo "PASS: format autodetection selected ttyrec and parsed the same frame"

echo
echo "its-playback-time ${EXPECTED_COMMIT}: all 14 assertions passed"