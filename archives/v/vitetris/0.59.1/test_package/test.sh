#!/usr/bin/env bash
# test_package/test.sh — vitetris 0.59.1 smoke test
#
# Verifies the installed `tetris` binary via its non-interactive entry points.
# vitetris uses `-help` (single dash) instead of `--help` / `--version`.
# The interactive game itself cannot be driven by CI, so we only exercise
# the non-interactive entry points and assert on their stdout.

set -euo pipefail

echo "[test] tetris -help prints version banner and usage"
help_output="$(tetris -help 2>&1)" || {
    echo "FAIL: tetris -help exited non-zero"
    echo "--- output ---"
    echo "$help_output"
    exit 1
}
[[ "$help_output" == *"vitetris 0.59.1"* ]] || {
    echo "FAIL: -help output missing version banner"
    echo "--- output ---"
    echo "$help_output"
    exit 1
}
[[ "$help_output" == *"-hiscores"* ]] || {
    echo "FAIL: -help output missing -hiscores option"
    echo "--- output ---"
    echo "$help_output"
    exit 1
}
[[ "$help_output" == *"-nomenu"* ]] || {
    echo "FAIL: -help output missing -nomenu option"
    echo "--- output ---"
    echo "$help_output"
    exit 1
}

echo "[test] tetris -hiscores prints highscore list and exits cleanly"
# On a fresh install this prints "No saved scores" and exits 0.
# On a system with saved scores it prints a highscore table.
# Either outcome is acceptable; a non-zero exit or missing keyword is not.
hiscores_output="$(tetris -hiscores 2>&1)" || {
    echo "FAIL: tetris -hiscores exited non-zero"
    echo "--- output ---"
    echo "$hiscores_output"
    exit 1
}
[[ "$hiscores_output" == *"scores"* ]] || {
    echo "FAIL: -hiscores output missing 'scores' keyword"
    echo "--- output ---"
    echo "$hiscores_output"
    exit 1
}

echo "[test] vitetris smoke test: PASS"
