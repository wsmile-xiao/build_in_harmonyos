# gtest 1.17.0.1 knowledge-upgrade evidence

## Candidate

- Source PR: #8612, `fix/gtest-1.17.0.1`
- Baseline and validated commit: `955c6872def6495ac549a83817613dafe756c90b`
- Candidate: Conan CMakeDeps must export the upstream `GTest` configuration and the four `gtest`, `gtest_main`, `gmock`, and `gmock_main` components with their `requires` relationships.
- Excluded duplicate: the OHOS `TMPDIR` patch is already covered by E292 and remains part of the original package adaptation.

## Evidence

| ID | Source | Result |
|---|---|---|
| EVID-01 | #8612 `conanfile.py` at `955c6872` | `cmake_file_name=GTest`; four CMake component targets and dependencies are declared. |
| EVID-02 | #8612 `test_package/` at `955c6872` | Consumer requests `find_package(GTest CONFIG)`, links `GTest::gtest_main` and `GTest::gmock`, and runs two assertions. |
| EVID-03 | AtomGit CI #41096 | Conan `test_package`, L0, and L1 passed for `archives/g/gtest/1.17.0.1`. |
| EVID-04 | #8612 body and existing `gtest/1.17.0` record | Historical upstream inventory is 65 binaries, 59/65 previously passed on OHOS; current 1.17.0.1 HEAD did not rerun that suite. |

## De-duplication

E292 covers GTest/CTest runtime migration, including writable `TMPDIR`, test data, loader, and test-framework boundaries. The existing gtest/1.17.0 adaptation records static libraries and the same TMPDIR portability patch. Neither describes the Conan CMake configuration-name and component-export contract validated by the new consumer. This candidate is therefore a new, narrow dependency-contract entry rather than a second TMPDIR entry.

## Limits

The original PR did not preserve a failing pre-fix consumer log. The old lowercase export is established by the existing 1.17.0 recipe and the new consumer's explicit `GTest` requests; the failure mode is documented as a static contract mismatch, not as an invented historical run. Shared-library consumers, non-CMake consumers, and a fresh full upstream CTest run for 1.17.0.1 remain unverified.
