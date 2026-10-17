#!/bin/sh
set -eu

abx_bin="$1"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work_root=${TMPDIR:-$PWD}
test_dir="$work_root/abx-test-$$"
mkdir -p "$test_dir"
trap 'rm -rf "$test_dir"' EXIT HUP INT TERM

python_bin=${PYTHON:-}
if test -z "$python_bin"; then
    python_bin=$(command -v python3)
fi
"$python_bin" "$script_dir/generate_wavs.py" "$test_dir"

sample_a="$test_dir/sample-a.wav"
sample_b="$test_dir/sample-b.wav"
sample_short="$test_dir/sample-short.wav"
sample_invalid="$test_dir/invalid.wav"
printf '%s\n' 'not a sound file' > "$sample_invalid"

test -f "$abx_bin"
test -x "$abx_bin"

# These paths return before GTK opens a display.
version_output=$("$abx_bin" --version 2>&1)
printf '%s\n' "$version_output" | grep -Fx -- "abx 0.1"

help_output=$("$abx_bin" --help 2>&1)

printf '%s\n' "$help_output" | grep -F -- "Usage:"
printf '%s\n' "$help_output" | grep -F -- "--num-trials=N"
printf '%s\n' "$help_output" | grep -F -- "--audio-device=ID"
printf '%s\n' "$help_output" | grep -F -- "--latency=L"
printf '%s\n' "$help_output" | grep -F -- "--self-test A B"

# The installed binary opens and reads both WAV files through its production
# libsndfile wrapper, exercises seek/read, executes eight ABX trials and the
# p-value calculation, checks GTK3's object model, and initializes PortAudio.
set +e
self_test_output=$("$abx_bin" --self-test "$sample_a" "$sample_b" 2>&1)
self_test_rc=$?
set -e
printf '%s\n' "$self_test_output"
if test "$self_test_rc" -ne 0; then
    exit "$self_test_rc"
fi
printf '%s\n' "$self_test_output" | grep -F -- "abx self-test: PASS"
printf '%s\n' "$self_test_output" | grep -F -- "files=2"
printf '%s\n' "$self_test_output" | grep -F -- "frames=800"
printf '%s\n' "$self_test_output" | grep -F -- "trials=8"
printf '%s\n' "$self_test_output" | grep -F -- "gtk=3."
printf '%s\n' "$self_test_output" | grep -E -- "portaudio-host-apis=[0-9]+"
printf '%s\n' "$self_test_output" | grep -E -- "portaudio-devices=[0-9]+"

# Both malformed inputs must fail closed with a stable diagnostic.
if "$abx_bin" --self-test "$sample_a" "$sample_short" >"$test_dir/duration.log" 2>&1; then
    printf '%s\n' "mismatched-duration self-test unexpectedly succeeded" >&2
    exit 1
fi
grep -F -- "audio fixtures have different geometry" "$test_dir/duration.log"

if "$abx_bin" --self-test "$sample_a" "$sample_invalid" >"$test_dir/invalid.log" 2>&1; then
    printf '%s\n' "invalid-audio self-test unexpectedly succeeded" >&2
    exit 1
fi
grep -F -- "cannot open audio fixture" "$test_dir/invalid.log"

printf '%s\n' "abx test_package: PASS"
