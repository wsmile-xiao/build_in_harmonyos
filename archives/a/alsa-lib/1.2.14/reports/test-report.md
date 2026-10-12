# alsa-lib 1.2.14 target test report

## Status

Both artefact modes were built and tested on the OpenHarmony PC target with the
native aarch64-linux-ohos clang 15.0.4 toolchain. `conan create` returned 0 in
both runs, the two registered upstream Automake entries passed, and all 11
independent consumer entries passed. Logical result: 13/13 (100%). Shared and
static runs validate artefact modes and are not added together.

## Log retention note

The raw full logs are local reproduction artefacts and are **not** part of the
pull request — only the three report files are committed (`test-report.md`,
`conan-verify-report.md`, `pr-body.md`). Every log path below is the local
reproduction path, and the conclusive excerpts are inlined here so the
assertions can be checked without the raw logs.

| Mode | Log (local) | Lines | Exit code | SHA256 |
|---|---|---|---|---|
| shared | `_scratch/alsa-w0/logs/conan-create-shared.final.log` | 2143 | 0 | `4632b6e1d7e3808175196c189467961e2d3c297f457dc5034fe329fe3f24e6d7` |
| static | `_scratch/alsa-w0/logs/conan-create-static.log` | 2140 | 0 | `4465113424f973eaad8af733d7da2d735135ba5f9116a211272a3e3bb5e45447` |

Reproduction command (identical to `ci/conan/build_and_test.sh`):

```bash
conan create archives/a/alsa-lib/1.2.14 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build="alsa-lib/*"
# static mode adds: -o "alsa-lib/*:shared=False" -o "alsa-lib/*:fPIC=True"
```

## Upstream boundary

Exactly two entries are registered through `TESTS` in `test/lsb/Makefile.am`:

```
TESTS  = config
TESTS += midi_event
```

The inventory (19 unregistered `check_PROGRAMS`, source SHA256 evidence) is in
`reports/upstream-test-inventory.md`. `make check` is executed inside the
recipe's `build()`, so `conan create` cannot succeed without running the
upstream suite:

```
make -j1 check LOG_COMPILER=/system/bin/timeout AM_LOG_FLAGS=180
```

`LOG_COMPILER` is pointed at a launcher written by the recipe so that both
extension-less scripts and ELF programs are wrapped by `/system/bin/timeout 180`
(the E228 launcher pattern).

## Upstream result

### Test command

```
make -j1 check LOG_COMPILER=/system/bin/timeout AM_LOG_FLAGS=180
```

### Case totals (real execution, both modes)

| Mode | Total | Passed | Failed | Skipped | XFAIL | XPASS | ERROR |
|---|---|---|---|---|---|---|---|
| shared | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| static | 2 | 2 | 0 | 0 | 0 | 0 | 0 |

### Per-case result

| Case name | Source | Registration | shared | static |
|---|---|---|---|---|
| `lsb-config` | `test/lsb/config.c` | `TESTS = config` | PASS | PASS |
| `lsb-midi-event` | `test/lsb/midi_event.c` | `TESTS += midi_event` | PASS | PASS |

### Raw Automake output (shared, log lines 1621-1634)

```
make  check-TESTS
make[4]: Entering directory '.../build-release/test/lsb'
PASS: config
PASS: midi_event
============================================================================
Testsuite summary for alsa-lib 1.2.14
============================================================================
# TOTAL: 2
# PASS:  2
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
============================================================================
```

### Result-file assertions

The recipe asserts that the `.trs` set is exactly
`{test/lsb/config.trs, test/lsb/midi_event.trs}` and that each file contains
exactly these four terminal fields:

```
:test-result: PASS
:global-test-result: PASS
:recheck: no
:copy-in-global-log: no
```

An extra, missing, failed or re-checked result aborts the build.

## Consumer entries (HarmonyOS)

`test_package/` compiles and **executes** 11 independent consumers on the
target. Each has its own executable and a 180-second external timeout.

| ID | Source | Lines executed on target |
|---|---|---|
| `AL-FUN-001` | `format_roundtrip.c` | format name/value and width contract |
| `AL-FUN-002` | `areas_silence.c` | bounded interleaved silence, sentinels intact |
| `AL-FUN-003` | `areas_copy.c` | offset interleaved copy, sentinels intact |
| `AL-FUN-004` | `null_playback.c` | null playback lifecycle |
| `AL-FUN-005` | `null_capture.c` | null capture lifecycle (uses patch 0007) |
| `AL-FUN-006` | `topology_roundtrip.c` | topology manifest round-trip |
| `AL-PKG-001` | `component_asound.c` | `ALSA::asound` version + runtime load |
| `AL-PKG-002` | `component_atopology.c` | `ALSA::atopology` version + closure |
| `AL-PKG-003` | `conanfile.py` | relocated pkg-config + 2 runtime consumers |
| `AL-PKG-004` | `conanfile.py` | artefact/ABI contract (see below) |
| `AL-PKG-005` | `feature_contract.c` | generated feature metadata + runtime env |

Measured: shared 11/11 PASS, static 11/11 PASS. Log trailer:

```
alsa-lib/1.2.14 (test package): validated 11 independent ALSA test-package entries
```

Representative inlined log lines (shared):

```
PASS AL-FUN-001: format name/value and width contract
PASS AL-FUN-005: null capture lifecycle completed without writing data
PASS AL-PKG-001: libasound component version 1.2.14
PASS AL-PKG-004: artifact and ABI contract
PASS AL-PKG-005: runtime metadata loaded the packaged ALSA configuration
```

`AL-PKG-004` is one failure unit covering: unversioned OHOS shared objects,
SONAME/NEEDED, the static archives, the static `fPIC` whole-archive shared-link
regression, headers, configuration files, CMakeDeps/PkgConfigDeps metadata, the
exact signed-ELF manifest and the licence.

## Build-only evidence (not counted as tests)

| Item | shared | static |
|---|---|---|
| public ABI link probes (`api_probe.c`) | 60/60 compiled | 60/60 compiled |
| upstream `check_PROGRAMS` built | 19 | 18 |
| excluded in static | — | `oldapi` (requests `snd_pcm_hw_params_get_access@ALSA_0.9`) |
| static `fPIC` whole-archive shared link | — | 1/1 |

These take function addresses only, are never executed, and are deliberately
excluded from the test counts.

## Artefacts

| Mode | Files | Notes |
|---|---|---|
| shared | `lib/libasound.so` (1043840 B), `lib/libatopology.so` (125504 B), `bin/aserver` (47680 B) | all `DYN` ELF, all carry a non-empty `.codesign` section |
| static | `lib/libasound.a` (1764760 B), `lib/libatopology.a` (234484 B), `bin/aserver` (699584 B) | no `.so` anywhere in the package |

Both modes ship headers, `share/alsa` configuration and pkg-config metadata
with a relocatable `prefix=${pcfiledir}/../..`, plus
`share/alsa/conan-elf-signatures.json` recording the signed package ELF hashes.
