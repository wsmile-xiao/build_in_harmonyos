# libeot 0.01 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang (profile `ohos-aarch64`, `tools.build:compiler_executables` → `/data/service/hnp/bin/clang`)
- Conan 2.29.1 (OHOS-adapted)
- Date: 2026-09-18

## Verification

- `conan-verify libeot 0.01`: PASS — G0 pass, G1 pass, G2 pass (clean `conan create`
  with test_package execution), G3 pass, G4 pass, L2 pass, L4 pass, L5 pass
  (`reports/conan-verify-report.md`)
- W3 local CI simulation (finish step 5/10, `ci/conan/setup.sh` + `build_and_test.sh`):
  exit 0 (`reports/w3-local-ci.log`):
  - G0_RESULT=pass
  - L0_RESULT=pass: all checks passed
  - L1_RESULT=pass: test_package executed
  - L2_RESULT=skip: eot2ttf version/help failed — the tool intentionally has no
    `--version`/`--help` options (argc != 3 prints usage and exits 1); the CI
    smoke probe treats this as a non-blocking warning
  - L4_RESULT=pass: patches clean
  - L5_RESULT=pass: bin/ has content
- `.ci-result.json`: exit_code 0 (the integrity hash is per-round because every
  validation round uses a private CONAN_HOME with a random name; the bound log
  is `reports/w3-local-ci.log`)

## test_package

1. Consumer program `libeot_test` (real execution on the device):
   `libeot consumer test: all 23 checks passed`
   - EOT v1 metadata parsing (EOTfillMetadata: version, fontDataSize,
     fontDataOffset == 96, flags, weight), EOTgetMetadataLength,
     EOTcanLegallyEdit, EOT2ttf_buffer (success + byte-identical conversion),
     EOTfreeBuffer/EOTfreeMetadata, UTF-16 family-name parsing ("Test"),
     negative paths (truncated input → EOT_INSUFFICIENT_BYTES, corrupt version
     magic → EOT_CORRUPT_FILE), EOTprintError.
2. Packaged `eot2ttf` tool roundtrip (invoked by explicit path from the
   package bindir, E529): `eot2ttf fixture.eot roundtrip.ttf`; output compared
   byte-wise against `expected.ttf` — identical.

- Test cases: 2
- Assertions: 24 (23 in the consumer program + 1 byte-compare)
- Passed: 2
- Failed: 0
- Skipped: 0

## Upstream tests

Upstream tag v0.01 ships no test suite: the source tree has no `tests/`
directory and `Makefile.am` defines no `TESTS`/`check` target, so there are
0 runnable upstream test entries. Evidence and the upstream test inventory are
in `notes.md` and `test_package/MANIFEST.yml`.

## Result

The recipe was verified on an OpenHarmony aarch64 device with the reviewed CI
profile; W3 local CI simulation passed. Status: built (published status
requires release upload evidence).
