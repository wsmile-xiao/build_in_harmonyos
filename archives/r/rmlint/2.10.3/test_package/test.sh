#!/bin/bash
# test_package/test.sh - consumer tests for rmlint on HarmonyOS PC.
#
# Usage: test.sh <bin_dir> <work_dir> <summary_file>
#
# Design constraints measured on the target (see notes.md):
#   * HMDFS rejects link(2) with EPERM, so no test here creates a hard link.
#     rmlint's own detection path does not need hard links.
#   * user.* xattrs do round-trip on HMDFS, but rmlint only writes them in the
#     optional xattr mode, so caching is exercised without depending on it.
#   * /tmp is a read-only erofs mount => the scratch tree is created under the
#     caller supplied work_dir inside the Conan build folder.
#   * HarmonyOS has no passwd DB entry for app uids, so getpwuid() returns
#     NULL and the default finder set flags every file as "Bad UID";
#     duplicate assertions therefore run with -T df (duplicates only).
#   * rmlint 2.x exits 0 after a *successful* scan even when waste was
#     found (measured; see rm_cmd_main in lib/cmdline.c). Findings are
#     asserted via the report text below, never via the exit code.
#
# Every case appends a "PASS:<name>" marker to the summary file; the recipe
# re-reads that file and fails if any marker is missing.

BIN_DIR="$1"
WORK="$2"
SUMMARY="$3"

RMLINT="$BIN_DIR/rmlint"
[ -x "$RMLINT" ] || RMLINT="$(command -v rmlint)"

: > "$SUMMARY"
say() { printf '[rmlint-test] %s\n' "$1"; }
ok()  { printf 'PASS:%s\n' "$1" >> "$SUMMARY"; say "PASS $1"; }
die() { printf 'FAILED:%s\n' "$1" >> "$SUMMARY"; say "FAILED $1"; say "detail: $2"; exit 1; }

[ -n "$RMLINT" ] || die "locate_binary" "no rmlint in $BIN_DIR nor on PATH"
[ -f "$RMLINT" ] || die "locate_binary" "$RMLINT is not a regular file"

rm -rf "$WORK"
mkdir -p "$WORK" || die "prepare_workdir" "cannot create $WORK"

PAYLOAD="$WORK/payload"
mkdir -p "$PAYLOAD/sub" || die "prepare_workdir" "cannot create $PAYLOAD"
i=0
while [ "$i" -lt 128 ]; do
    printf 'rmlint-fixture-block-%04d-abcdefghijklmnopqrstuvwxyz0123456789\n' "$i"
    i=$((i + 1))
done > "$PAYLOAD/original.txt"
cp "$PAYLOAD/original.txt" "$PAYLOAD/sub/copy.txt" || die "prepare_workdir" "cp failed"

CLEAN="$WORK/clean"
mkdir -p "$CLEAN" || die "prepare_workdir" "cannot create $CLEAN"
printf 'content alpha\n' > "$CLEAN/alpha.txt"
printf 'content beta\n'  > "$CLEAN/beta.txt"

EMPTY="$WORK/empties"
mkdir -p "$EMPTY/an_empty_dir" || die "prepare_workdir" "cannot create $EMPTY"

# ---------------------------------------------------------------------------
say "case 1: --version"
"$RMLINT" --version > "$WORK/version.out" 2>&1
rc=$?
[ "$rc" -eq 0 ] || die "version_flag" "rmlint --version exited $rc; output: $(head -3 "$WORK/version.out")"
grep -qi 'rmlint' "$WORK/version.out" || die "version_flag" "no program name in version output"
grep -q '[0-9]' "$WORK/version.out"   || die "version_flag" "no version number in version output"
ok "version_flag"

# ---------------------------------------------------------------------------
say "case 2: --help"
"$RMLINT" --help > "$WORK/help.out" 2>&1
rc=$?
[ "$rc" -eq 0 ] || die "help_flag" "rmlint --help exited $rc"
grep -q 'duplicate' "$WORK/help.out" || grep -qi 'usage' "$WORK/help.out" \
    || die "help_flag" "help output carries neither usage nor duplicate"
grep -qi 'xattr' "$WORK/help.out" \
    || die "help_flag" "expected xattr related options missing from help"
ok "help_flag"

# ---------------------------------------------------------------------------
say "case 3: duplicate detection on the real filesystem"
# -T df restricts the run to the duplicate finder: without it every file
# lands in the baduid finder first on HarmonyOS (no passwd DB entry).
"$RMLINT" -T df "$PAYLOAD" > "$WORK/dup.out" 2>&1
rc=$?
# rmlint 2.x exits 0 for a successful scan; the twins are asserted below.
[ "$rc" -eq 0 ] || die "duplicate_detected" \
    "expected exit 0 (successful scan), got $rc; output: $(head -20 "$WORK/dup.out")"
grep -q 'original.txt' "$WORK/dup.out" || die "duplicate_detected" "first twin not reported"
grep -q 'copy.txt' "$WORK/dup.out"     || die "duplicate_detected" "second twin not reported"
grep -qi 'duplicate' "$WORK/dup.out"   || die "duplicate_detected" "no duplicate summary line"
ok "duplicate_detected"

# ---------------------------------------------------------------------------
say "case 4: machine readable report via the json output formatter"
# -o fmt:path directs the json formatter to a file (a bare -O path is not a
# formatter spec and would leave report.json unwritten). The output path must
# be pure ASCII: glib converts option values from the locale encoding and
# under the C locale aborts on any byte > 0x7F (measured; this worktree path
# contains non-ASCII characters), so the report goes to ASCII $HOME/tmp and
# is removed again below.
# CI worker 的 $HOME/tmp 可能不存在且不可写（PR #12551 #60514 实测）：
# 运行时探测可写目录，回退到测试自身工作目录 $WORK（CI 检出路径为纯 ASCII）
REPORT_DIR="$HOME/tmp"
mkdir -p "$REPORT_DIR" 2>/dev/null || true
if [ ! -d "$REPORT_DIR" ] || [ ! -w "$REPORT_DIR" ]; then REPORT_DIR="$WORK"; fi
REPORT="$REPORT_DIR/rmlint-case4-report.$$.json"
rm -f "$REPORT"
"$RMLINT" -T df -o "json:$REPORT" "$PAYLOAD" > "$WORK/json.stdout" 2>&1
rc=$?
[ "$rc" -eq 0 ] || die "json_formatter_output" \
    "scan exited $rc; output: $(head -20 "$WORK/json.stdout")"
[ -s "$REPORT" ] || die "json_formatter_output" "json report file missing or empty"
grep -q 'original.txt' "$REPORT" || die "json_formatter_output" "json report lacks first twin"
grep -q 'copy.txt' "$REPORT"     || die "json_formatter_output" "json report lacks second twin"
grep -qi '"size"' "$REPORT"      || grep -qi 'checksum' "$REPORT" \
    || die "json_formatter_output" "json report carries neither size nor checksum field"
rm -f "$REPORT"
ok "json_formatter_output"

# ---------------------------------------------------------------------------
say "case 5: negative control - a tree without duplicates must stay silent"
# -T df mirrors case 3/4 (on HarmonyOS the default set flags every file
# baduid first), and the summary line always contains the word
# "duplicates", so assert the exact zero-groups line instead of a keyword.
"$RMLINT" -T df "$CLEAN" > "$WORK/clean.out" 2>&1
rc=$?
[ "$rc" -eq 0 ] || die "clean_tree_reports_nothing" \
    "expected exit 0 on a clean tree, got $rc; output: $(head -20 "$WORK/clean.out")"
grep -q '0 are duplicates in 0 groups' "$WORK/clean.out" \
    || die "clean_tree_reports_nothing" "summary does not report zero duplicate groups"
grep -q 'alpha.txt' "$WORK/clean.out" \
    && die "clean_tree_reports_nothing" "distinct file listed as duplicate"
ok "clean_tree_reports_nothing"

# ---------------------------------------------------------------------------
say "case 6: empty directory finder type (-T ed)"
"$RMLINT" -T ed "$EMPTY" > "$WORK/empty.out" 2>&1
rc=$?
[ "$rc" -eq 0 ] || die "empty_dir_type" \
    "expected exit 0 for a successful scan, got $rc; output: $(head -20 "$WORK/empty.out")"
grep -q 'an_empty_dir' "$WORK/empty.out" || die "empty_dir_type" "empty dir not reported"
grep -qi 'empty' "$WORK/empty.out" || die "empty_dir_type" "no empty-type summary line"
ok "empty_dir_type"

say "all cases finished"
exit 0
