#!/bin/bash
# Consumer-side verification of the installed transfuse artifacts.
#
# Every check below drives the executable that was actually installed into the
# package bin/ directory, so the whole script fails once bin/ is taken away
# (which is exactly what the CI L1e destructive check relies on).
set -u

PASS=0
FAIL=0

fail() {
	printf 'FAIL: %s\n' "$*" >&2
	FAIL=$((FAIL + 1))
}

pass() {
	printf 'ok: %s\n' "$*"
	PASS=$((PASS + 1))
}

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ── 1. the executables are installed and are real OHOS arm64 ELFs ────────
TF="$(command -v transfuse 2>/dev/null || true)"
if [ -z "$TF" ]; then
	printf 'FAIL: transfuse is not on PATH; the package bin/ directory is missing or empty\n' >&2
	printf 'RESULT: %d passed, %d failed\n' "$PASS" "$FAIL" >&2
	exit 1
fi
[ -x "$TF" ] && pass "transfuse found and executable ($TF)" || fail "transfuse is not executable"

if head -c 4 "$TF" | od -An -tx1 | tr -d ' \n' | grep -qi '^7f454c46'; then
	pass "transfuse is an ELF binary"
else
	fail "transfuse is not an ELF binary"
fi

# ── 2. version string comes from the built config.hpp ─────────────────────
VERSION="$("$TF" --version 2>/dev/null || true)"
case "$VERSION" in
	*0.7.6*) pass "--version reports 0.7.6 ($VERSION)" ;;
	*) fail "--version did not report 0.7.6 (got: $VERSION)" ;;
esac

# ── 3. the three upstream aliases are installed ───────────────────────────
for alias in tf-extract tf-inject tf-clean; do
	if command -v "$alias" >/dev/null 2>&1; then
		pass "alias $alias installed"
	else
		fail "alias $alias is missing from bin/"
	fi
done

# ── 4. HarmonyOS-specific end-to-end check ───────────────────────────────
# Extract a UTF-8 HTML document that mixes plain text, a <b> inline span and
# non-ASCII characters.  Getting this right exercises the whole stack at
# once: libxml2 parses the document, ICU lower-cases the inline span, xxhash
# derives the [tf-block:N-<hash>] identifiers, and the formatter re-emits the
# span markers.  The expected file is the checked-in golden output.
#
# transfuse emits a NUL byte as the block separator.  Those bytes are stripped
# from the produced output here and were stripped from the checked-in golden
# file as well, which is what keeps the golden file plain text -- otherwise Git
# classifies it as binary and the PR diff becomes a binary patch the CI worker
# cannot apply.  Everything the assertions look at (the [tf-block:N-<hash>]
# identifiers, the [[t:b:...]] inline span markers and the UTF-8 payload) is
# unaffected by the removal.
IN="data/test-ohos.html"
GOLDEN="data/test-ohos.expect"

if [ ! -f "$IN" ] || [ ! -f "$GOLDEN" ]; then
	fail "test data missing ($IN / $GOLDEN)"
else
	"$TF" -v -m extract -K -s apertium "$IN" "$WORK/out.tmp" >/dev/null 2>"$WORK/err.txt"
	RC=$?
	if [ "$RC" -ne 0 ]; then
		fail "transfuse extract exited $RC"
		sed -n '1,10p' "$WORK/err.txt" >&2
	else
		grep -aEv '^\[transfuse:' "$WORK/out.tmp" \
			| grep -aEv '^<STREAMCMD:TRANSFUSE:' \
			| tr -d '\000' > "$WORK/out.txt"

		if grep -aq '^\[tf-block:' "$WORK/out.txt"; then
			pass "extract emitted [tf-block:N-<hash>] block markers"
		else
			fail "extract produced no [tf-block:] markers"
		fi

		if grep -aq '\[\[t:b:[A-Za-z0-9]*\]\]HarmonyOS\[\[/\]\]' "$WORK/out.txt"; then
			pass "extract emitted the <b> inline span as [[t:b:...]]...[[/]]"
		else
			fail "extract did not emit the expected <b> inline span"
		fi

		if grep -aq 'Ünïcödé and 中文字符 stay intact' "$WORK/out.txt"; then
			pass "UTF-8 round-tripped (Ünïcödé / 中文字符)"
		else
			fail "UTF-8 content was mangled"
		fi

		if diff -u "$GOLDEN" "$WORK/out.txt" > "$WORK/diff.txt" 2>&1; then
			pass "extract output matches the golden file byte for byte"
		else
			fail "extract output differs from the golden file"
			sed -n '1,20p' "$WORK/diff.txt" >&2
		fi
	fi
fi

# ── 5. the clean mode round-trips back to a document ─────────────────────
if [ -f "$IN" ]; then
	"$TF" -v -m clean -K -s apertium -d "$WORK/clean" "$IN" "$WORK/clean.out" >/dev/null 2>&1
	RC=$?
	if [ "$RC" -eq 0 ] && grep -aq 'HarmonyOS' "$WORK/clean.out"; then
		pass "clean mode rebuilt a document containing the original text"
	else
		fail "clean mode exited $RC or lost the text"
	fi
fi

printf 'RESULT: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0