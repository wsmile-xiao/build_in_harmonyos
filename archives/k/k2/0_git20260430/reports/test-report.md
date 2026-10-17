# k2 0_git20260430 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4 (OHOS cross toolchain, profile `ohos-aarch64`)
- Conan 2.29.1

## Verification

- `ohc-run.py conan-verify k2 0_git20260430`: exit 0
  - G1 recipe integrity: PASS
  - G2 clean `conan create` + test_package: PASS
  - G3 R26 system-library isolation: PASS (pure executable, no lib/)
  - G4 artifact integrity: PASS (L2/L4/L5 platform checks skipped — no cache path)
- W3 local CI simulation (`finish` pipeline): exit 0, **pass rate 100% (1/1)**
  - L0 quality gates: passed
  - L1 official test (test_package): passed — "test_package executed"
  - L1e R34 negative test: passed — `bin/` sabotaged (moved away) → test fails →
    "test genuinely depends on k2"
  - L4 static scan on patches: passed — "patches clean"
  - L5 artifact baseline: passed — "bin/ has content"

## test_package (UCI functional test)

The test runner `test_k2.py` (consumer smoke-test pattern, same as ympd) feeds UCI
command sequences into the packaged `k2` binary and asserts that the protocol
answers appear on stdout. It is invoked by `test_package/conanfile.py` with the
packaged binary path (`env="conanrun"`):

| # | Test case | Input | Assertion | Result |
|---|-----------|-------|-----------|--------|
| 1 | UCI identification | `uci` + `quit` | stdout contains `uciok` | PASS |
| 2 | Readiness | `isready` + `quit` | stdout contains `readyok` | PASS |
| 3 | Real search | `position startpos` + `go depth 4` | stdout contains `bestmove` | PASS |

- Test cases: 3
- Passed: 3
- Failed: 0
- Skipped: 0

## Device functional smoke (multi-threaded prod build)

- `uci` → `uciok`; `isready` → `readyok`
- `position startpos` + `go depth 5` → `bestmove e2e4`
- `position startpos moves e2e4 e7e5 g1f3 b8c6 f1b5 a7a6` + `go depth 7` →
  `bestmove b5c6` (captures the e5 pawn — correct for the position)

## Upstream test suite (R51)

- `make test` builds `test_all` (49 test functions, 513 assert statements:
  bitboards / board / chess / eval / engine / time management, incl. perft,
  SEE, move generation & legality, checkmate detection).
- One stale upstream assert fixed (patch `0001-test_all.cpp.patch`,
  platform-independent bug: `double_pawns()` only detects single-square
  adjacent pawns; see notes.md).
- Result: **49/49 test functions pass** — `./test_all` → "All tests passed",
  exit 0.

## Result

`k2/0_git20260430` builds and verifies successfully on `aarch64-linux-ohos`;
status `built` (binary verified locally, not uploaded to the artifact registry).
