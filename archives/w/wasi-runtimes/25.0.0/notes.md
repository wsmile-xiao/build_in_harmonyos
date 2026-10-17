# wasi-runtimes 25.0.0 OpenHarmony PC notes

## Scope

This package adapts the runtime assets from the official `WebAssembly/wasi-sdk` release `wasi-sdk-25`. It packages:

- `wasi-sysroot-25.0.tar.gz`
- `libclang_rt.builtins-wasm32-wasi-25.0.tar.gz`

These assets provide the WASI sysroot headers/libraries and compiler-rt builtins used by WASI consumers.

## Dependency boundary

The `wasi-sdk` source repository does not contain all compiler/runtime source code directly; it relies on large LLVM, wasi-libc, and compiler-rt inputs. Rebuilding the full SDK would be a toolchain build, not a normal library recipe, and is unsuitable for the contest CI space budget. This recipe therefore packages the official release runtime assets instead of fabricating a local LLVM build. There is no OHOS-native runtime API in this package; the consumable interface is the WASI sysroot/header/library layout plus the compiler-rt builtins archive used by downstream WASI toolchains.

## Build

No source patch or local compilation is required. The package phase installs:

- `share/wasi-sysroot/**`
- `share/wasi-sysroot/lib/wasm32-wasi/libclang_rt.builtins-wasm32.a`
- `share/wasi-sysroot/.wasi-assets.json` (generated file inventory used by test_package)

## Tests

Upstream `wasi-sdk-25` does contain a `tests/` suite (`tests/compile-only` and `tests/general`, driven by `tests/CMakeLists.txt` and `tests/testcase.sh`). Those tests compile C/C++ against a full WASI clang/LLVM toolchain and execute the resulting `.wasm` binaries with a `runwasi` runner, so they cannot be executed inside this runtime-assets-only package.

The `test_package` therefore validates the complete packaged inventory instead of fabricating upstream coverage. `package()` writes `.wasi-assets.json` with every file shipped from the official `wasi-sysroot-25.0` and `libclang_rt.builtins-wasm32-wasi-25.0` archives (6552 files), and `check_wasi_assets.py` verifies that every listed file exists with the expected size. It also checks representative header markers in `stdio.h` and `stdlib.h`, plus `ar` archive magic for `libc.a` and `libclang_rt.builtins-wasm32.a`.

## Verification status

OpenDesk queue job `20260814-070628-bfc89f-20260814-misc2-3053-3057-3058-r1` on head `87fead37c` passed `ci/conan/build_and_test.sh` with Build Summary Total 1 / Success 1 / Failed 0. `check_wasi_assets.py` verified all 6552 packaged files from the official wasi-sdk-25 archives, and `test_package` output `WASI runtime assets packaged and structurally validated (6552 files from official wasi-sdk-25 archives)`.

## Verification command

```bash
CI_PACKAGES="archives/w/wasi-runtimes/25.0.0" zsh ci/conan/build_and_test.sh
```
