#!/usr/bin/env bash
# End-to-end check of the packaged dawgdic-build / dawgdic-find tools:
# build dictionaries from a small lexicon and query them back.
# Fixture layout mirrors the upstream test/ lexicon + query + answer files.
set -eu
# pipefail is bash-only; enable when available but stay runnable under /bin/sh.
set -o pipefail 2>/dev/null || true

bindir="$1"
build_bin="${bindir}/dawgdic-build"
find_bin="${bindir}/dawgdic-find"

# E002: OHOS /tmp is read-only; mktemp must use writable TMPDIR.
# Prefer hmbs-injected writable dir; never fall back to bare /tmp.
# ${VAR:-} guards keep 'set -u' safe under both bash and /bin/sh.
_pick_tmpdir() {
  for v in "${TMPDIR:-}" "${HMBS_TMPDIR:-}" "${TEMP:-}" "${TMP:-}" "${HMBS_AUTOCONF_MKTEMP_FALLBACK:-}"; do
    if [ -n "$v" ] && [ "$v" != "/tmp" ] && [ "$v" != "0" ] && mkdir -p "$v" 2>/dev/null; then
      printf '%s' "$v"
      return 0
    fi
  done
  printf '%s' "$PWD"
}
_TMPROOT="$(_pick_tmpdir)"
workdir="$(mktemp -d "$_TMPROOT/dawgdic-test-XXXXXX")"
trap 'rm -rf "${workdir}"' EXIT
cd "${workdir}"

printf 'a\t1\nan\t0\nand\t2\napple\t1\nbin\t2\n' > lexicon
printf 'a\nan\nand\napple\nbin\navocado\n' > query
printf 'a: a = 1;\nan: a = 1; an = 0;\nand: a = 1; an = 0; and = 2;\napple: a = 1; apple = 1;\nbin: bin = 2;\navocado: a = 1;\n' > expected
printf 'a: a = 1 an = 0 and = 2 apple = 1\nan: an = 0 and = 2\nand: and = 2\napple: apple = 1\nbin: bin = 2\navocado:\n' > expected-guide

"${build_bin}" -t lexicon lexicon.dic
"${find_bin}" lexicon.dic < query > result
if cmp result expected; then
  echo "[PASS] dawgdic-build/dawgdic-find round trip"
else
  echo "[FAIL] dawgdic-build/dawgdic-find round trip"
  diff -u expected result || true
  exit 1
fi

# Guided completion path (-g) must agree with the plain dictionary.
"${build_bin}" -gt lexicon lexicon-guide.dic
"${find_bin}" -g lexicon-guide.dic < query > result-guide
if cmp result-guide expected-guide; then
  echo "[PASS] dawgdic-build/dawgdic-find guided round trip"
else
  echo "[FAIL] dawgdic-build/dawgdic-find guided round trip"
  diff -u expected-guide result-guide || true
  exit 1
fi

echo "ALL TOOL TESTS PASSED"
