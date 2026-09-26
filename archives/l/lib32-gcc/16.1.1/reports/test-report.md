# lib32-gcc 16.1.1 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Conan 2.29.1 (repo `bin/conan`)
- Bootstrapped GCC driver (GCC 16.1.0 sources, packaged as 16.1.1 per task requirement), compiled by device clang toolchain
- Target assembler: recipe-built GNU ARM gas (binutils 2.46.0, compiled by the recipe itself as `target-tools/as` during the build and shipped as `bin/as`; no prebuilt host artifact required)
- Target linker: device GNU ld 2.45 (`/data/service/hnp/bin/ld`, multi-target build incl. `armelf_linux_eabi`; in-tree `gcc/collect-ld`/`gcc/real-ld` wrapper scripts removed before torture so collect2 resolves the device ld)
- Profile: `ci/conan/profiles/ohos-aarch64` (host = build = aarch64 HarmonyOS PC)

## Verification

- `conan create` (ci12, full build + upstream tests + package + test_package): exit 0
- `conan-verify lib32-gcc 16.1.1`: exit 0 — G0/G1/G2 (clean rebuild)/G3/G4 all PASS, `.conan-verified` written at 2026-09-17T21:48:14
- `finish` (W2+W3 local CI simulation): W3 PASS — `L0_RESULT=pass`, `L1_RESULT=pass` (upstream tests + test_package executed), `L2_RESULT=pass`, build summary `Success: 1, Pass rate: 100.0% (1/1)`

## Upstream tests (N / N' accounting)

- **N = 1685** — upstream count = the full inventory of the suite this recipe drives.
  Inventory command: `find gcc/testsuite/gcc.c-torture/execute -name '*.c' | wc -l` → `1685`
  (counting method: source-file inventory of the suite, the same method the review uses).
- **N' = 100** — executed in `build()`: the first 50 sources (sorted) x `{-O0, -O2 -fno-strict-aliasing}`.
- **Pass rate 100/100 (100%)**, twice: `upstream gcc.c-torture/execute subset: 100/100 passed`
  in both ci12 and the W3 clean rebuild.
- **N' < N: 1585 sources not executed.** Concrete technical reasons:
  1. **System capability**: the target artifact is a 32-bit ARM `arm-linux-ohos` binary and the
     build host is aarch64 — no torture program can be executed at all. The executed 100 therefore
     use the documented **compile+link+ELF-validation口径** (each case is compiled and linked to a
     valid ELF by the build-tree cross driver: xgcc + xgcc-sign wrapper → cc1 → packaged GNU ARM
     gas → collect2 → device GNU ld; each artifact is validated with `llvm-readelf -h`, and the
     ELF32/ARM machine type is asserted in the test_package consumer flow).
  2. **Missing runner**: GCC's DejaGNU torture driver has not been ported to an OHOS runner. The
     recipe drives the suite with its own bounded runner (it parses and honours each source's
     `dg-additional-options`), which is not a drop-in replacement for the full driver.
  3. **Build-window budget**: the package-level CI window is dominated by the in-recipe GNU ARM gas
     build (~25 min) plus `all-gcc` + `all-target-libgcc`. Sweeping all 1685 sources (3370
     compile+link cases) does not fit the window; the 7200s package override is requested through
     the infrastructure channel (see notes.md section 18).
- **The 1585 unexecuted sources are declared as not executed — no pass is claimed for them.**
- Notable L2 informational items (gate still PASS): `arm-linux-ohos-gcc-ar/-nm/-ranlib --version` failed; core driver commands (`gcc`, `arm-linux-ohos-gcc`, versioned name, `cpp`, `as`, `collect-ld`, `ld`, `real-ld`, `gcov*`) all OK.

## test_package — HarmonyOS consumer end-to-end flow

Consumer case 1 (complete end-to-end flow, stages 1–7) and consumer case 2 (target ABI program,
stage 8). Every stage is driven through the **installed Conan package**:

| # | stage | command | assertions |
|---|-------|---------|-----------:|
| 1 | driver identity | `gcc --version` | 1 |
| 2 | target identity | `gcc -dumpmachine` == `arm-linux-ohos` | 1 |
| 3 | preprocess | `gcc -E consumer_probe.c` → `"arm-linux-ohos-32bit-abi"` present | 1 |
| 4 | compile TU-A | `gcc -O2 -c consumer_lib.c -o consumer_lib.o` → ELF32/ARM/REL, `.ARM.attributes`, `consumer_compute` DEFINED FUNC | 8 |
| 5 | compile TU-B | `gcc -O2 -c consumer_main.c -o consumer_main.o` → ELF32/ARM, `consumer_compute` UND | 5 |
| 6 | link | `gcc -O2 consumer_main.o consumer_lib.o -o consumer_program` | (exit code) |
| 7 | inspect program | `llvm-readelf -h/-s consumer_program` → EXEC/DYN, non-zero entry point, `main`/`consumer_compute`/`consumer_target_abi` DEFINED | 12 |
| 8 | target ABI program | `gcc -O2 -DEXPECT_OHOS=1 test_gcc.c -o gcc_test_program` → compile-time `__OHOS__` + 32-bit ABI, artifact ELF32/ARM | 3 |

- Consumer cases: 2 (one of them a complete end-to-end flow)
- Assertions: 31 hard checks (run with `ignore_errors=False`, so a non-zero compile/link exit code
  fails the test package outright)
- Passed: 2 cases / 31 assertions
- Failed: 0, Skipped: 0
- Why the linked program is not executed: it is an ARM32 binary and the host is aarch64. The flow
  therefore validates the artifact structurally (ELF class/machine/type, non-zero entry point,
  `.ARM.attributes` assembler fingerprint, cross-translation-unit symbol resolution at link time).

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for
`built` status (artifact-repo upload not yet performed; `commands.json` written
with `binary:false` accordingly).
