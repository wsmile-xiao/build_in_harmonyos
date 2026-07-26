# HarfBuzz 14.2.0 Conan recipe

## Scope

This version provides a source-built Conan 2 recipe for HarfBuzz 14.2.0. It uses the official release archive, depends on `freetype/2.14.3`, and publishes core, subset, and vector library components. No prebuilt binary is committed.

## Configuration

- Build system: Meson
- Library modes: shared and static through the standard Conan option
- OHOS toolchain handling: explicit Meson `ar`/`ranlib` paths resolved by the same version-aware helper as the test/signing tools, plus post-install shared-library signing
- Upstream test tool handling: on Linux/OHOS, absolute `NM`/`OBJDUMP` paths are resolved from Conan's configured clang with the original symbol and static-initializer checks retained; Windows/MSVC keeps upstream Meson behavior
- Review hardening: partial buffer-allocation failures are cleaned up; signing tools are resolved without fixed Worker paths, and all dynamic signing-command paths are POSIX-shell quoted
- Static consumer metadata: propagates `pthread` and `m` from upstream `Libs.private`
- Enabled: FreeType, subset, vector, upstream tests
- Disabled: glib, gobject, cairo, chafa, png, zlib, ICU, graphite, raster, GPU, introspection, documentation, utilities, benchmark
- Patches: none

## Local validation

- WSL Ubuntu with Clang 15/libc++ and Conan 2.29.1
- shared `conan create`: passed
- static `conan create`: passed
- shared upstream Meson tests: 59/59 passed, 0 failed, 0 skipped
- static upstream Meson tests: 57 passed, 0 failed, 2 shared-library-only checks skipped
- consumer shaping test: 1/1 passed in both modes

WSL is a Linux/x86_64 approximation. HarmonyOS/aarch64 status must be determined by repository CI on the submitted HEAD.

PR #2906 Build #7523 compiled successfully but ended with 56 passed, 2 failed, and 1 skipped upstream groups because OHOS Python could not launch bare `llvm-nm` and `llvm-objdump` names. The recipe injects resolved absolute paths for those two original checks; follow-up Build #7546 passed all CI steps on HEAD `636741ba00a19aa07b87af58309a67603ddf7f67`.

Initial AI Review findings were applied: the consumer test destroys a non-NULL buffer when internal allocation fails, and the OHOS signing step resolves `llvm-objcopy` and `binary-sign-tool` through the active toolchain/PATH instead of hard-coded Worker locations.

The second AI Review finding was also applied: Meson's `ar` and `ranlib` injection now calls the same version-aware resolver, so `clang-15` consistently selects `llvm-ar-15` and `llvm-ranlib-15`.

Build #7584 passed all CI steps on follow-up HEAD `6de3ea24626b8b0b00feebd494289aa8e039fa23`. The third AI Review finding was then applied locally: `shlex.join()` now serializes the resolved `llvm-objcopy`, `binary-sign-tool`, input-library, and output-library arguments without unsafe shell path concatenation. A new formal CI run is required after this change is pushed.
