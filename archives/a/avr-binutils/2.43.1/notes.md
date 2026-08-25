# avr-binutils 2.43.1 adaptation notes

Issue: #2244

## W0

- Runtime dependencies: none beyond the OHOS base system.
- Build prerequisites: GNU make, sh, Clang/LLVM tools, and binary-sign-tool from the CI image.
- Optional test dependency: DejaGNU/runtest is not published in the ohpcd Conan remote.
- Downstream users: avr-gcc-bootstrap/14.2.0 and avr-libc/2.2.1.

## Build strategy

The binaries are OHOS/AArch64 host applications configured with
`--target=avr`. This is a Canadian-cross toolchain component, not a native
OHOS binutils replacement.

The release uses Autotools. Two portability patches add the OHOS GNU triplet
and change generated configure temporary-directory permissions for HMDFS.
Compiler wrappers run through the system shell and sign every linked host ELF;
the package pass signs all installed ELF programs again. Pre-generated Info
documents from the official release are reused because Texinfo is not a declared
build dependency.

The build disables GDB, gprofng, gold, simulator, plugins, NLS, shared
libraries, debuginfod, Guile, and zstd. These components are not needed by
the AVR compiler bootstrap.

## Tests

- Upstream source contains 25,185 testsuite files and 372 DejaGNU driver
  scripts. The full target matrix is skipped when `runtest` is unavailable.
- `make -C libiberty check` runs six official no-DejaGNU checks.
- The package test executes the packaged AVR assembler, linker, objcopy,
  objdump, nm, readelf, and size tools. It creates an ATmega328P object,
  AVR ELF, and Intel HEX file and validates architecture and symbols.
- AVR code is not executed on the OHOS host.

## True-device shadow CI

- Device: OHOS/AArch64 through the global single-package runner.
- Tested recipe commit: `025ba666fdac38d42d5feefa534388111a3b22ca`.
- Shadow commit: `66a185f1b5dfc310b5a6ba52b891201a9c70a88a`.
- Run: `codex-avr-binutils-shadow-ci-r5-2244-20260817-134800-3191`.
- Result: G0, L0, L1, L2, and L5 passed; 16 packaged commands passed
  version checks; the substantive package test and destructive negative test
  passed.
- L4 reported a non-blocking dangerous-function warning in the portability
  patch; no runtime failure or gate failure resulted.

## Single-package CI

```sh
CI_PACKAGES="archives/a/avr-binutils/2.43.1" zsh ci/conan/build_and_test.sh
```

### Review-ready pass rates

- Upstream `libiberty`: 6/6 passed (100%).
- Packaged AVR command checks: 16/16 passed (100%).
- Conan `test_package`: 1/1 passed (100%).
- Package-content negative gate: 1/1 passed (100%).
- Full DejaGNU matrix: 0 executed, pass rate N/A; the unavailable `runtest`
  and Expect dependency is not counted as a pass and is tracked separately
  from this package adaptation.

## CI #30506 incident

- Head: `85690b2083ad818c1040865789125973d4f6b18c`.
- Build: #30506 / build 34178 on `OpenHarmonyPCDeveloper-CI-031`.
- G0, L0, KC, and package structure checks passed. `conan-build-test`
  stopped during the Autotools host compiler probe with `C compiler cannot
  create executables` and Conan error 77.
- The same head passed CI #30354 on CI-044 and CI #30418 on CI-041 without
  recipe changes. The failure is therefore recorded as a Worker environment
  incident pending inspection of `config.log`, the OHOS clang/sign wrapper,
  and temporary-directory execution permissions. This failed retry is not
  counted as a passing test.
