# YAHA 0.1.83 test report

> **Test date:** 2026-10-05
> **Environment:** HarmonyOS 6.0, aarch64/armv8, OHOS Clang 15.0.4
> **Test type:** Conan package build and consumer test, plus native HarmonyOS device run

## Summary

The upstream v0.1.83 source has no automated test suite or registered test target (0 upstream tests). `make check` was attempted on the clean source on HarmonyOS and reported that no such target exists. The Conan consumer test passed on the HarmonyOS aarch64 profile and on a HarmonyOS 6.0 device.

| Measure | Result |
|---|---:|
| Upstream automated tests | 0 |
| Conan consumer test scripts | 1 passed / 1 |
| SAM output fields checked | 10 passed / 10 |
| W3 package builds | 1 passed / 1 |
| Conan verification | PASS (G0–G4) |

## HarmonyOS-specific functional test

The test runs the packaged `bin/yaha` executable on the HarmonyOS 6.0 aarch64 device from HNP Bash. It creates an index from a small reference, then aligns matching 50-base reads from both FASTA and FASTQ input with two threads. The resulting SAM records are checked for QNAME, FLAG, reference name, position, and CIGAR for each input format. Both records mapped to `chr1:21` with `50M` (10 field-level checks in total).

This exercises the target binary, file I/O, index generation, sequence parsing, multithreaded alignment, and SAM output on HarmonyOS; it is not a pure assertion-only test.

## Verification details

- `conan create` built the package with profile `ohos-aarch64` (`os=OHOS`, `os.version=6.0`, `arch=armv8`, `compiler=clang`, `compiler.version=15`, Release) and executed `test_package` successfully.
- W3 local CI: L0, L1, L4, and L5 passed. L1 confirms `test_package` was executed; L4 found no dangerous patch functions; L5 confirmed the packaged `bin/` artifact exists.
- W3 L2 was skipped because the generic smoke check's `--version`/`--help` options are not supported by this CLI. The consumer test separately executes the upstream `yaha -xh` help option successfully.
- Conan verification reported PASS for G0–G4. L2/L4/L5 were marked PASS by the verifier with cache-based subchecks skipped because no cache path was supplied.

## Upstream test census (R51)

- Source tree directories: `src/` and `testdata/`; no `tests/` directory.
- Registered tests: 0 standalone test files, 0 CTest registrations, 0 pytest registrations.
- The upstream `testdata/README.txt` explains example input datasets; it does not define an automated test runner.
- Upstream entrypoint attempt on the clean HarmonyOS source: `make check` → `No rule to make target 'check'` (exit 2). There are no upstream test cases to report as a passing fraction.

## Build fix

The OHOS Clang build exposed repeated default arguments on the `findAffineGapScore` template definition after its forward declaration. The package patch removes the repeated defaults from the definition and preserves them on the declaration. The rebuilt source then passed Conan creation and the consumer test.

## Artifacts

- `test_package/test.sh` — creates the reference index, aligns FASTA and FASTQ reads, and validates SAM fields.
- `reports/conan-verify-report.md` — Conan verification summary.
- `reports/w3-local-ci.log` and `reports/conan-create.log` — local working evidence (not intended for PR submission).
