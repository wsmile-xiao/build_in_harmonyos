# abx 0.1 upstream test inventory

Date: 2026-08-17

## Audit scope

The pristine `abx_0.1.orig.tar.gz` source tree and both Automake inputs were
inspected before recipe authoring.

## Findings

- No `tests/` or `test/` directory exists.
- Top-level `Makefile.am` contains only `SUBDIRS = src`.
- `src/Makefile.am` declares only `bin_PROGRAMS = abx` and the application's
  production sources.
- There is no `TESTS`, `check_PROGRAMS`, `check_SCRIPTS`, CTest, Meson test, or
  custom test target.
- `src/test.c` and `src/test.h` are misleadingly named production modules. They
  implement trial state, answer/guess storage, and binomial p-value calculation
  and are linked into `abx`; they do not contain a test entry point.

## Build-stage test decision

There is no meaningful upstream suite to execute. The recipe records that fact
instead of running an empty Automake `check` target and counting it as coverage.

## Consumer coverage

The adaptation does not relabel its new checks as upstream tests. The installed
binary exposes a deterministic `--self-test` entry solely for package/runtime
validation. `test_package/test_abx.sh` records 37 assertions across four
scenarios:

- package, version, help, and real option discovery;
- deterministic WAV metadata, PCM read/seek, close, and geometry checks through
  the production libsndfile wrapper;
- eight production ABX trials, answer/guess roundtrips, bounds rejection, and
  exact binomial p-value;
- headless GTK3 object use, PortAudio initialization/inventory/termination, and
  two fail-closed malformed-input paths.

PortAudio currently exposes no HarmonyOS host API or device, so hardware
playback remains outside the validated scope.
