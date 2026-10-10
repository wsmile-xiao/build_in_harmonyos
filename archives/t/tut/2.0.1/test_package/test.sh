#!/bin/sh
# test_package/test.sh — smoke test for tut executable.
# Runs in conanrun env (PATH includes installed bin/).
# Uses /bin/sh per HMBS injection (SHELL=/bin/sh); do not hardcode bash.
set -eu

echo "[test] tut --help"
HELP_OUT=$(tut --help 2>&1)
echo "$HELP_OUT" | head -20
case "$HELP_OUT" in
  *tut*|*Usage*|*usage*|*Commands*|*commands*|*help*)
    echo "[ok] --help prints usage"
    ;;
  *)
    echo "[fail] tut --help output unexpected"
    exit 1
    ;;
esac
if [ -z "$HELP_OUT" ]; then
  echo "[fail] tut --help output is empty"
  exit 1
fi

echo "[test] tut --version"
VER_OUT=$(tut --version 2>&1)
echo "$VER_OUT"
case "$VER_OUT" in
  *[0-9]*)
    echo "[ok] --version prints a version"
    ;;
  *)
    echo "[fail] tut --version output has no digit"
    exit 1
    ;;
esac
if [ -z "$VER_OUT" ]; then
  echo "[fail] tut --version output is empty"
  exit 1
fi

echo "[test] tut example-config"
WORK=$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/tut-test-$$")
mkdir -p "$WORK"
if tut example-config 2>&1 | head -5; then
  echo "[info] example-config ran in build dir"
fi
# example-config writes ./config.example.toml in cwd; run it inside WORK
# so we do not pollute the conan test folder, then verify non-empty.
(cd "$WORK" && tut example-config >/dev/null 2>&1) || true
if [ -f "$WORK/config.example.toml" ]; then
  if [ -s "$WORK/config.example.toml" ]; then
    echo "[ok] example-config produced non-empty config.example.toml"
    head -5 "$WORK/config.example.toml"
  else
    echo "[fail] config.example.toml is empty"
    rm -rf "$WORK"
    exit 1
  fi
else
  # Fallback: some builds write to cwd of the first invocation.
  if [ -f "./config.example.toml" ] && [ -s "./config.example.toml" ]; then
    echo "[ok] example-config produced non-empty ./config.example.toml"
  else
    echo "[fail] example-config produced no config file"
    rm -rf "$WORK"
    exit 1
  fi
fi
rm -rf "$WORK"

echo "[ok] all 3 tut smoke checks passed"
