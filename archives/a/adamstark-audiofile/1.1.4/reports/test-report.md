# adamstark-audiofile 1.1.4 Test Report

- Date: 2026-08-06
- Upstream source SHA-256: `e3749f90a9356b5206ef8928fa0a9c039e7db49e46bb7f32c3963d6c44c5bea8`
- Recipe revision: `a7ff7212e3c9eff7a817eb10b20e0466`
- Package ID: `da39a3ee5e6b4b0d3255bfef95601890afd80709`

## Upstream Tests

The official upstream CMake project registers one CTest entry named `Tests`.
The executable uses doctest and contains 73 test cases.

- Host CTest entries: 1/1 passed
- Host doctest test cases: 73/73 passed
- Host doctest assertions: 1,739,931/1,739,931 passed
- HarmonyOS PC W3 CTest entries: 1/1 passed

Public upstream test accounting uses 73/73. Assertion totals are recorded only
as supporting detail.

## Added Consumer Tests

The Conan `test_package` builds one independent consumer executable that checks
WAV memory round trip, AIFF memory round trip, and WAV filesystem round trip.
Those internal checks belong to one consumer flow and are not counted as
separate independent tests.

- HarmonyOS PC W3 consumer CTest entries: 1/1 passed
- HarmonyOS PC W3 direct consumer execution: passed
- Added independent consumer tests: 1/1 passed

## Evidence

- Host upstream report: `reports/upstream-host-tests.md`
- W0 dependency graph report: `reports/w0-dependency-graph-20260806.md`
- HarmonyOS PC W3 report: `reports/harmonyos-pc-device-w3-20260806.md`
- HarmonyOS PC W3 log: `E:\HarmonyPC\validation\adamstark-audiofile-1.1.4\w3-device-r2\conan-create.log`
