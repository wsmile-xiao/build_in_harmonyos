# mtoc 1035.1.102 Adaptation Notes

## Source Audit

- Primary source: Apple cctools tag `cctools-1035.1.102`.
- Primary SHA256: `1867fa0204c139f8073689b0d0785454b152b367762ff07ec9f316c97da1969b`.
- Portability source: cctools-port commit
  `904de2a71d4da6a9b30d2efaf912a10ddc7d9ddb`.
- Portability SHA256: `6809ba18b6b4f4646b17b1baba48f9a0cb94425cc334272918ba944fd7399b32`.

Both archives are fetched from their respective project repositories over
HTTPS and pinned by SHA256. The compatibility source contributes only the
non-Darwin foreign headers, `machine.h`, `port.h`, and `port.c`; the mtoc
implementation and all other linked libstuff sources remain Apple 1035.1.102.

## Build Strategy

Apple builds mtoc inside the larger cctools/Xcode build. The package adds a
small CMake wrapper that compiles `efitools/mtoc.c` with the 23 libstuff source
files needed by the executable. It defines the Darwin compatibility feature
macros used by cctools-port and links the platform dynamic-loader library when
present.

Conan maps its `armv8` setting to the recipe-specific CMake processor value
`aarch64`. For that processor, the wrapper also defines `__arm64__`, matching
the compatibility rule in cctools-port's `configure.ac`. The five BSD string
functions used by the compatibility headers are detected at CMake configure
time instead of being assumed from the host libc.

There are no Conan package dependencies. This satisfies the dependency
preflight without importing another package into the PR.

## Test Audit

The Apple release contains 103 cctools test-case directories. A source-tree
search finds no mtoc test case or mtoc invocation; the five similarly named
`mtor-*` cases test a different program. Homebrew's mtoc formula supplies a
downstream conversion smoke test, confirming that an end-to-end conversion is
the appropriate package-level test.

The added test builds a deterministic ARM64 `MH_PRELOAD` Mach-O image with a
single executable `__TEXT` segment and an ARM64 `ret` instruction. It runs the
packaged mtoc binary and verifies the DOS signature, PE offset and signature,
AArch64 machine type, section count, PE32+ optional-header type, EFI subsystem,
`.text` section metadata, and preservation of the instruction bytes. It also
checks the no-argument usage path and nonzero exit code. The test contains 18
explicit conditions in total.

The test emits numbered `[STEP]` records, the full external command, exit code,
stdout and stderr, and one `[PASS]` or `[FAIL]` record per assertion. It uses
the same entry point from Conan `test_package` and direct device validation.

## Upstream Baseline

| Item | Result |
| --- | --- |
| Source tag | `cctools-1035.1.102` |
| Source archive SHA256 | `1867fa0204c139f8073689b0d0785454b152b367762ff07ec9f316c97da1969b` |
| `tests/test-cases` directories | 103 |
| mtoc-specific upstream tests | 0 |
| similarly named `mtor-*` cases | 5, for a different executable |
| added package test | 1 integration scenario, 18 assertions |

The audit searched both `tests/` and `libstuff_test/` for mtoc invocations and
found none. No upstream test was removed or disabled.

## Dependency Preflight

- Direct Conan requirements: none.
- Transitive Conan requirements: none.
- W0 result: `required: []`.
- The remote version-occupancy probe was inconclusive because the package
  server returned `system acceleration policy not enabled`; it did not report
  a published `mtoc/1035.1.102` recipe.

## OHOS Failure-Driven Iterations

| Round | First failure | Root cause | Change | Result |
| --- | --- | --- | --- | --- |
| 1 | CMake saw `CMAKE_SYSTEM_PROCESSOR=unknown` | HarmonyOS has no CMake platform module that supplies the processor | Map Conan `arch=armv8` to `aarch64` | A standard CMake cache variable was overwritten; same failure remained |
| 2 | CMake still saw `unknown` | The platform initialization replaced the standard variable | Pass `MTOC_TARGET_PROCESSOR` and use it in the wrapper | Configure completed on OHOS |
| 3 | `architecture not supported` in cctools-port headers | OHOS Clang defines `__aarch64__`; the imported Darwin compatibility headers select ARM64 only with `__arm64__` | Define `__arm64__=1` for the mapped AArch64 target | Architecture selection fixed; exposed missing ARM alias directories |
| 4 | Source download timed out at `ghfast.top` | Fresh device had no Conan source cache and the injected mirror timed out | Seed Conan's SHA256-addressed source cache without changing official source URLs | Both archives retrieved from the local cache |
| 5 | `mach/arm/vm_types.h` and `mach/arm/boolean.h` missing; `rindex` redefined | cctools-port represents ARM host headers with directory symlinks that were lost in the HarmonyOS source/build copy; its `foreign/strings.h` also lacked a whole-file include guard | Materialize both ARM aliases as directories and add an idempotent header guard patch | OHOS clean Conan build and the 18-assertion package test pass |

The E538, E540, E537, and E529 knowledge-graph matches printed after these G2
failures concern unrelated dependency packages. The raw compiler diagnostics
above, rather than those fuzzy matches, determine each fix.

## Platform Difference Matrix

| Difference | Upstream behavior | OHOS evidence | Compatibility measure | Status |
| --- | --- | --- | --- | --- |
| Build entry | Xcode builds mtoc inside cctools | No standalone portable mtoc build | Focused CMake target with the 23 required libstuff sources | Linux pass; OHOS configure pass |
| CMake processor | Known Darwin/Linux processor | Reported `unknown` under `CMAKE_SYSTEM_NAME=HarmonyOS` | Recipe-specific processor derived from Conan `arch` | Fixed in OHOS round 2 |
| Architecture macro | cctools-port configure maps AArch64 to `__arm64__` | OHOS advanced beyond architecture selection after the macro was added | Define the same compatibility macro only for AArch64 | Fixed in OHOS round 3 |
| ARM header aliases | cctools-port uses `arm -> i386` and `mach/arm -> mach/i386` directory symlinks | HarmonyOS build folder lacked the aliased headers | Materialize both aliases from their upstream targets during `source()` | Fixed; OHOS build pass |
| libc string API | configure probes BSD string functions; compatibility header may be included transitively more than once | OHOS did not expose `rindex` to the probe and compiled its fallback twice | Probe five symbols and patch the fallback header with a whole-file include guard | Fixed; OHOS build pass |
| File and memory mapping | mtoc reads Mach-O through libstuff/ofile | Core conversion exercises this path | Retain cctools-port POSIX mmap shim; validate through conversion test | OHOS functional test pass |
| Endianness and width | 64-bit little-endian ARM input/output | Target is armv8/AArch64 | Explicit ARM64 fixture and PE machine/payload checks | OHOS functional test pass |
| Threads | No selected mtoc source requires threads | No thread dependency in recipe | N/A | N/A |
| Network and IPC | Core mtoc conversion is local-file-only | No reachable network/IPC source in target | N/A | N/A |
| Dynamic loading | Selected target does not include LLVM/LTO loader sources | No reachable `dlopen` path in mtoc target | N/A; `${CMAKE_DL_LIBS}` remains platform-derived | N/A |
| Generated build tools | No target code generator is required | Conan invokes CMake and the OHOS compiler directly | No build-context executable required | Confirmed |

## Validation

The same Apple source and pinned compatibility files were compiled on an
x86_64 Linux baseline with GCC 13. The resulting executable converted the
fixture successfully; `file` identified the output as `PE32+ executable (EFI
application) Aarch64`, and all 18 test conditions passed.

The final native OHOS run used HarmonyOS aarch64, Conan 2.29.1, the repository
`ohos-aarch64` profile, and Clang 15.0.4 targeting
`aarch64-unknown-linux-ohos`. Both pinned archives came from Conan's verified
download cache. The build applied the strings-header patch, linked `mtoc`, and
completed `test_package` with 18/18 assertions. A direct device rerun of the
same test entry point also returned `MTOC_TEST_EXIT=0`.

The produced executable is an AArch64 PIE using `/lib/ld-musl-aarch64.so.1`;
its only `DT_NEEDED` entry is `libc.so`. Its SHA256 is
`e3b11b77fdc3c2784ba767737c4480a487ba7eec39bd7b17b5fbed8848e6933c`.
The successful full package reference is
`mtoc/1035.1.102@ohpcd/stable#c8bad98314146227f9ac4a6f6a79ead4:6b129b068851896169fae42d399fa922d239ce8a#52049142a0d1ae8e9228e29719ef7fcb`.

The repository verifier did not resolve the dotted version to a cache package
for its optional G4/L2/L4/L5 follow-up checks. The exact package folder was
therefore inspected directly with `file`, `readelf`, SHA256, and the shared
functional test. The definitive `conan create` and direct runtime evidence both
pass. Official PR CI, `/rebuild`, `/ai review`, and review-thread closure remain
post-submission gates.

The platform findings are recorded here as package-level L3 knowledge. E092
already covers the general CMake platform-recognition family, while the ARM
aliases and fallback header guard follow the exact upstream cctools-port
layout; this submission therefore adds no separate knowledge-graph draft.

## Final Status

- Linux x86_64 clean `conan create`: COMPLETED, 1/1 scenario and 18/18
  assertions passed.
- HarmonyOS aarch64 `conan create`: COMPLETED; `test_package` and the direct
  device rerun each passed 1/1 scenario and 18/18 assertions.
- Package state: `built`; keep `commands.json` binary state false until
  artifact publication after merge.
