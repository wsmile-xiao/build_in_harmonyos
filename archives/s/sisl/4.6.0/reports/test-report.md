# sisl 4.6.0 test report

## Upstream test inventory (R51)
- Test directories: 0.
- Registered CTest cases: 0 (no `enable_testing()` or `add_test()` in root CMakeLists).
- Declared demo/example assets (PR body denominator): 26 = 3 `app/*.C` upstream-registered executables +
  23 `examples/**/*.cpp`. Of those, 19 carry `main()` and 7 are support translation units.
  The registered-CTest count and the asset count are two different口径 and are reported separately, never mixed.
- All 26 were processed on HarmonyOS PC on 2026-09-27 (runner `CIW-S4k3`): built, and run wherever a `main()` exists.
  See notes.md "Upstream test suite real execution" for the per-asset table and machine-readable summary.

## Local validation
- W0 device preflight: PASS; no Conan dependencies.
- CMake configure/build/install: PASS; one library staged.
- Generic `make check`: no target exists; consistent with the source inventory.
- Conan G2 attempt 1: FAIL while downloading through the injected ghfast.top mirror (timeout).
- Conan G2 attempt 2: FAIL on a SHA-256 typo; the checksum is now corrected.
- Conan G2 attempt 3: direct codeload download succeeded, but archive extraction inferred ZIP from the extensionless URL; conandata now specifies `filename: SISL-SISL-4.6.0.tar.gz`.
- Conan G2 attempt 4 reported PASS with a regenerated printf stub test. This is invalid under R34; its log/report are preserved outside the archive.
- Valid G2 rerun with the API-backed `newCurve`/`s1221` test passed; `conan-create.log` confirms `test_sisl` executed and passed.
- Historical resource-gate failures delayed the corrected G2 retry; it later passed. Evidence is under `~/tmp/uc2/sisl/build-gate-fail-001.txt` through `build-gate-fail-013.txt`.
- Finish attempted W3 local CI and failed before the SISL CI build: JC1/JC5 full-tree scan found tracked runtime markers in `archives/c/cloog/0.21.1` and `archives/k/kics/2.1.20`. Those unrelated archives were left untouched (`~/tmp/uc2/sisl/w3-local-ci-fail-001.txt`). W3 local CI was then re-run and PASSED: `.ci-result.json` exit_code 0, step W3_local_ci, timestamp 2026-09-23T18:59:39; `reports/w3-local-ci.log` ends Total 1 / Success 1 / Failed 0 with L0=pass L1=pass L2=skip(no bin/) L4=pass L5=pass. No PR created and nothing pushed.

## Counts (same source as test_package/MANIFEST.yml and notes.md)
| metric | value |
|---|---|
| upstream demo/example assets declared (PR body denominator, static count — counting commands in notes.md) | 26 |
| upstream CTest cases registered | 0 |
| upstream assets processed on device 2026-09-27 (built; those with main() also run) | 26 |
| upstream executable cases (carry main()) | 19 |
| upstream executable cases passed (really run) | 18 |
| upstream executable cases failed | 0 |
| upstream executable cases blocked | 1 (`examples/viewer/sisl_view_demo.cpp`, `GL/glut.h` not found) |
| upstream support translation units compiled | 3 |
| upstream support translation units blocked | 4 (missing `GL/glut.h` x3, `GL/glx.h` x1) |
| **upstream total passed / failed / blocked** | **21 / 0 / 5** |
| Go-format result files produced by the example chain | 23 (all non-empty) |
| upstream runner exit code | 0 |
| consumer tests registered | 1 (`test_sisl`) |
| consumer tests executed | 1 |
| consumer tests passed | 1 |
| assertions | 55 (4 in `test.c` + 51 upstream in-source status guards that stayed silent) |

**Verdict** PASS — 26/26 upstream declared assets processed on HarmonyOS PC: 21 passed, 0 failed, 5 blocked at
build by the platform's missing desktop OpenGL/GLUT stack, each with its first real error recorded in notes.md
("Upstream test suite real execution"). Nothing blocked is counted as passed.

Reproduce: `sh ~/tmp/uc2/gate.sh 8000 && sh ~/tmp/uc2/build-slot.sh --kind long --wait 3600 --mem 6000 -- sh ~/tmp/uc2/ciw-s4-sisl-b3/run_def.sh`
(device build host A; peak compiler RSS 152 MB, min MemAvailable 18.5 GB, concurrency 1).
