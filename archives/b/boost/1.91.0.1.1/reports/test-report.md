# Boost 1.91.0.1.1 Test Report

## Snapshot

- Run: `boost-1.91.0.1.1-redex-w3-r4`
- Frozen HEAD: `5116ab2fa920e2224098e41804c00feb82c241ca`
- Frozen candidate tree: `42457694d8ac540ffd46d54158c7a0310ccb7088`
- Result manifest SHA-256: `b6d3be7b0ba1d446c6e9e4a99967180b7fb627b2fb81adb97f16c78837795110`
- Normalized upstream log SHA-256: `f15bb093eac01ebcaa4d7ae3cc3a92a44407714ce91498b9929cdd50372b2477`

## Summary

| Result | Count | Evidence |
|---|---:|---|
| Total tests | 25 | 18 upstream plus 7 package consumers |
| Passed PASS | 25 | Shared and static variants both completed |
| Failed FAIL | 0 | Closed W3 evidence manifest |
| Skipped SKIP | 0 | No selected test was skipped |

The unique test count is 25/25 PASS. Shared and static executions are build
variants of the same inventory and are not counted twice.

## Upstream Tests

The source-derived inventory in `upstream-inventory.txt` contains 18 entries:
15 component CTest targets, the Iostreams `test_fd` integration flow, the Regex
`quick` flow, and the unmodified Boost.Graph disjoint-set leaf. Both package
variants completed all 18 entries: **18/18 PASS (100%)**.

## Added Consumers

Seven Conan consumers completed in both variants: component unit coverage,
Redex Iostreams usage, Atomic, DateTime, Graph, OHOS portability, and the new
Redex-shaped Multiprecision contract. The Multiprecision consumer includes
`cpp_int.hpp`, instantiates the fixed-width allocator-free `cpp_int_backend`,
and covers 8 of the suite's 31 assertions. Result: **7/7 PASS (100%)**.

## Artifact Audit

- Shared package: `boost/1.91.0.1.1#a87a5f6c933b59858076703e53cff426:01d92cf349a0dd98ff915f4bd99a04430171517f#978f06a635235df28409196d5aefb699`
- Static package: `boost/1.91.0.1.1#a87a5f6c933b59858076703e53cff426:21b17f8b2bc0e9511e276e3d57a23893067cefe5#d0c81c39274e78a17a81cfeb757d0ff8`
- Each package contains `boost/multiprecision/cpp_int.hpp`, the Multiprecision
  CMake target, 12 compiled libraries, and zero symlinks.
- Shared libraries are AArch64 ELF objects with `.codesign` sections.

## Evidence Boundary

The original shared and static logs remain outside the repository with hashes
`0e848ee0395d193e31947e13b24ddc6d4a5f962658c44dca476d789a0028e5e1`
and `e7a4be0db6f7dc791c6a7558a8d1ab2bb3263b080601882a34f818915b1a5298`.
`upstream-pass-summary.txt` was generated only after validating those immutable logs,
the remote result SHA manifest, accounting files, artifact audits, and terminal
W3 PASS. No binary artifact is committed or uploaded by this PR.
