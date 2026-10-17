# libnoise 1.0.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device, native build
- Clang 15.0.4 (OHOS SDK), Conan 2.29.1 (OHOS-adapted), CMake via the CI
  toolchain, `shared=False` default (static library)
- Per-round validation runs in a task-private Conan home (`CCACHE_DISABLE=1`)
  so every `conan create` is a full clean rebuild

## Verification

- `conan create` (via `conan-verify` G2): exit 0 — compiles the exact
  35-translation-unit list from the upstream `noise/src/Sources` file with
  the recipe-shipped CMakeLists.txt; zero patches, zero source modifications
  (`reports/conan-create.log`, `reports/conan-verify-report.json`).
- Conan verify gates: G0, G1, G2, G3, G4 plus L2/L4/L5 — all passed
  (`reports/conan-verify-report.json`, verdict PASS; L2 skip reason: the
  package installs no `bin/` executables — library only).
- W3 local CI (`build_and_test.sh`, same source as线上 CI):
  - L0: passed (structure, test sources, MANIFEST.yml, recipe/data syntax)
  - L1: passed — test_package executed by conan create; L1e R34 destructive
    negative test (lib/ and include/ moved away) confirmed the consumer
    binary genuinely depends on the packaged library
  - L2: skip — no bin/ directory (library package)
  - L4: passed (no dangerous-function findings, no patches)
  - L5: passed — `lib/` contains the installed library
  Evidence: `reports/w3-local-ci.log` (hash-anchored in the round's
  `.ci-result.json`), refreshed every validation round.

## Upstream test suite

Upstream 1.0.0 ships **no test suite**: the source zip contains only
COPYING.txt, doc/, include/, lib/, src/, win32/ MSVC project files and the
hand-written Makefiles; there is no tests/ directory, no
enable_testing()/add_test() anywhere and no `check` target in any Makefile
(top-level goals: all/clean/install/doc/src/include/lib). Inventory evidence
is recorded in `../notes.md`. Upstream runnable test entries: 0/0.

## test_package (installed-package consumer test)

One program is built against the installed package and executed:

| Program | What it verifies | Checks | Result |
|---|---|---|---|
| `test_libnoise` | Perlin determinism/finiteness/coherence, distant-input separation, parameter setters, Billow and RidgedMulti generators, ScaleBias module graph (exact source*scale+bias IEEE arithmetic), ExceptionNoModule contract of unconnected source modules, Sphere/Cylinder/Plane/Line model layer, LatLonToXYZ unit-sphere properties | 16 | PASS |

- Test cases: 1 — consumer program output:
  `libnoise consumer test: 16 checks, 0 failures`
- Assertions: 16
- Passed: 1 (16/16 assertions)
- Failed: 0
- Skipped: 0

## Packaging / staging

The packaged deliverable is assembled from the round's actual Conan package
folder (`include/`, `lib/libnoise.a`, `licenses/COPYING.txt`) into
`packaging/libnoise-1.0.0-ohos-aarch64.tar.gz` and re-verified by extracting
it into a clean staging prefix: 44 headers under `include/noise/`
(9 root + 30 module + 5 model, matching the upstream include/Makefile
layout — the MSVC resource shim win32/ is excluded), 35 object members in
`lib/libnoise.a` (llvm-ar), byte-identical `libnoise.a` between tarball and
cache package, no empty files, no bin/. The verification marker is
`.staging-verified` (gitignored, device-local like the tarball).

## Result

The recipe was verified on an OpenHarmony aarch64 device and holds
`built` status (verified, not yet released/uploaded).
