#!/bin/bash
# test_package/test.sh -- end to end test of the installed dicom3tools programs.
#
# Run inside the conanrun environment, so that every program invoked below is
# the one that was just packaged.  All the assertions in this script were
# checked by hand against the built programs; the exit codes quoted in the
# comments are the observed ones.
#
# dicom3tools is a set of separate command line programs rather than a library,
# so the test drives the real binaries: dccreate writes a Part 10 DICOM file
# from nothing, and the other tools read it back.  The file is generated at run
# time because the repository forbids adding binary fixtures -- the platform
# generated pr.diff carries no binary patch body and CI's `git apply` would fail
# before the build even started.
# -o pipefail 保留管道中的失败；刻意不启用 -e：本脚本用 $? 判定坏输入必须失败，
# 启 -e 会让这些断言在判定前就退出。
# 刻意偏离 code-style 的 `set -euo pipefail`，只用 `set -uo pipefail`：
# 本脚本的多条断言要求「坏输入必须以非 0 退出」（见下方 dcdump/dciodvfy 两条），
# 启 -e 会让脚本在断言判定之前直接退出，反而掩盖结果。失败状态由末尾的
# `[ "$fail" -eq 0 ]` 兜底，因此非 0 退出仍然成立（该偏离已在 notes.md 显式声明）。
set -uo pipefail

# Work in a temporary directory and always remove it: the generated DICOM files
# must never end up in the package source tree, because a binary file in the PR
# diff makes CI's `git apply` fail before the build starts.
WORK="$(mktemp -d "${TMPDIR:-.}/dicom3tools-test.XXXXXX")" || exit 1
trap 'rm -rf "$WORK"' EXIT INT TERM
cd "$WORK" || exit 1

pass=0
fail=0

ok() {
	pass=$((pass + 1))
	echo "PASS: $1"
}

bad() {
	fail=$((fail + 1))
	echo "FAIL: $1"
}

# ---------------------------------------------------------------- availability
for tool in dccreate dcdump dciodvfy dckey dcdict dcstats dccp; do
	if command -v "$tool" >/dev/null 2>&1; then
		ok "found $tool"
	else
		bad "missing $tool"
	fi
done

# ------------------------------------------------------------------- 1. create
# dccreate builds a Part 10 file from the command line alone; it needs a study
# identifier as well as a patient identifier to work out the SOP class.
if dccreate test.dcm -r PatientID 123 -r StudyID 456 -r PatientName "Test^Patient" \
	-nodisclaimer >create.log 2>&1; then
	ok "dccreate wrote a DICOM file (rc=0)"
else
	bad "dccreate failed (rc=$?, see create.log)"
fi

if [ -s test.dcm ]; then
	ok "created file is non-empty ($(wc -c <test.dcm) bytes)"
else
	bad "created file is empty or missing"
fi

# DICOM Part 10: a 128 byte preamble followed by the "DICM" magic.
if [ "$(dd if=test.dcm bs=1 skip=128 count=4 2>/dev/null)" = "DICM" ]; then
	ok "file has the Part 10 DICM magic at offset 128"
else
	bad "file is not a Part 10 DICOM file"
fi

# --------------------------------------------------------------------- 2. dump
# dcdump writes its listing to stderr, so both streams are captured.
dcdump test.dcm >dump.out 2>&1
if grep -q "Patient ID" dump.out && grep -q "123" dump.out; then
	ok "dcdump read back the Patient ID that was set"
else
	bad "dcdump did not report the Patient ID"
fi

if grep -q 'Test\^Patient' dump.out; then
	ok "dcdump read back the Patient Name that was set"
else
	bad "dcdump did not report the Patient Name"
fi

if grep -q "1.2.840.10008.1.2.1" dump.out; then
	ok "explicit VR little endian transfer syntax recorded in the meta header"
else
	bad "transfer syntax missing from the file meta information"
fi

# --------------------------------------------------------- 3. data dictionary
if dcdict -key PatientName 2>&1 | grep -q "(0x0010,0x0010)"; then
	ok "dcdict resolved PatientName to (0x0010,0x0010)"
else
	bad "dcdict did not resolve PatientName"
fi

if dcdict -key PatientName 2>&1 | grep -q "PN"; then
	ok "dcdict reports the PN value representation"
else
	bad "dcdict did not report the value representation"
fi

# dckey describes a tag as well; it exits 0 and prints the tag and VR.
if dckey -key PatientName 2>&1 | grep -q "(0x0010,0x0010)"; then
	ok "dckey described the PatientName tag"
else
	bad "dckey did not describe the PatientName tag"
fi

# ------------------------------------------------------------- 4. validation
# The created file is deliberately minimal, so dciodvfy reports conformity
# problems (rc=1).  What matters here is that it parses the file that
# dccreate produced and comments on it.
dciodvfy test.dcm >iodvfy.out 2>&1
if [ -s iodvfy.out ]; then
	ok "dciodvfy produced a validation report"
else
	bad "dciodvfy produced no output"
fi

if grep -qi "Dicom dataset read failed" iodvfy.out; then
	bad "dciodvfy could not read the file dccreate produced"
else
	ok "dciodvfy read the file dccreate produced"
fi

# ------------------------------------------------------------------ 5. stats
# The file has no pixel data, so dcstats must say so rather than crash.
dcstats test.dcm >stats.out 2>&1
if grep -q "PixelData" stats.out; then
	ok "dcstats reported the missing pixel data"
else
	bad "dcstats did not report the missing pixel data"
fi

# ------------------------------------------------------- 6. reject bad input
# A truncated data set must be reported as a read failure (observed rc=1).
dd if=test.dcm of=truncated.dcm bs=1 count=200 2>/dev/null
dcdump truncated.dcm >truncated.out 2>&1
truncated_rc=$?
if [ "$truncated_rc" -ne 0 ] && grep -q "Dicom dataset read failed" truncated.out; then
	ok "dcdump rejected a truncated data set (rc=$truncated_rc)"
else
	bad "dcdump accepted a truncated data set (rc=$truncated_rc)"
fi

# Plain text is not a Part 10 file and must not validate (observed rc=1).
printf 'this is not a dicom file at all, it is plain text\n' >garbage.dcm
dciodvfy garbage.dcm >garbage.out 2>&1
garbage_rc=$?
if [ "$garbage_rc" -ne 0 ]; then
	ok "dciodvfy rejected a non-DICOM file (rc=$garbage_rc)"
else
	bad "dciodvfy accepted a non-DICOM file"
fi

# -------------------------------------------------------------- 7. round trip
# Re-encode through dccp and require the result to still be Part 10 DICOM.
if dccp test.dcm -justmeta >roundtrip.dcm 2>roundtrip.log; then
	if [ -s roundtrip.dcm ] && [ "$(dd if=roundtrip.dcm bs=1 skip=128 count=4 2>/dev/null)" = "DICM" ]; then
		ok "dccp re-encoded the file meta information ($(wc -c <roundtrip.dcm) bytes)"
	else
		bad "dccp produced a file that is not Part 10 DICOM"
	fi
else
	bad "dccp failed to re-encode the file (see roundtrip.log)"
fi

echo
echo "dicom3tools test_package: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
