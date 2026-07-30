# HarfBuzz 14.2.0 adaptation notes

## Build

- Build system: Meson
- Conan package type: library with `harfbuzz`, `subset`, and `vector` components
- Options: `shared=True/False`, `fPIC`
- Dependency: `freetype/2.14.3`
- Patches: none
- Status: built locally, not published

The dependency recipe builds FreeType without HarfBuzz, so the Conan graph has no cycle. `PkgConfigDeps` generates `freetype2.pc`; Meson receives its path from the generated native file. Conan's standard `shared` option supplies `default_library`, while the recipe enables FreeType, subset, vector, and tests and disables unrelated optional integrations and utilities.

The recipe resolves LLVM tools from Conan's configured C compiler through one shared resolver. On Linux/OHOS it injects absolute `ar` and `ranlib` paths into Meson's native file, and supplies absolute `NM` and `OBJDUMP` paths while running the upstream test suite; other platforms keep Meson's native behavior. Versioned compilers retain their suffix consistently, for example `clang-15` selects `llvm-ar-15`, `llvm-ranlib-15`, `llvm-nm-15`, and `llvm-objdump-15`. This keeps HarfBuzz's symbol and static-initializer checks active even when OHOS Python does not resolve bare commands through `posix_spawn`, without forcing Windows/MSVC to provide Unix tools. On OHOS shared builds, installed libraries are re-signed after Meson rewrites ELF metadata; both `llvm-objcopy` and `binary-sign-tool` are resolved to absolute paths from the toolchain directory or `PATH`, and every dynamic command argument is POSIX-shell quoted before execution. Static consumers receive the upstream `-pthread -lm` private link requirements through the core component.

No prebuilt archive, manually generated `hb-features.h`, glib dependency, or amalgamated-source fallback is part of this recipe.

## Validation

- WSL Ubuntu, Clang 15, libc++, Conan 2.29.1; Linux/x86_64 approximation only
- shared: `conan create` passed
- static: full `conan create` passed and packaged three static libraries
- shared upstream suite: 59/59 Meson test groups passed, 0 failed, 0 skipped
- static upstream suite: 57 passed, 0 failed, 2 shared-library-only checks skipped
- consumer test: 1/1 shaping pipeline passed with 7 glyphs in both modes
- packaged libraries: `harfbuzz`, `harfbuzz-subset`, `harfbuzz-vector`

Log:

- `E:/HarmonyPC/validation/batch-20260717-deps/harfbuzz-conan-create-shared.log`
- `E:/HarmonyPC/validation/batch-20260717-deps/harfbuzz-conan-create-static-final.log`

The WSL run took substantially longer in the template-heavy repacker test compile. These results do not replace HarmonyOS/aarch64 CI evidence.

## Formal CI follow-up

- PR #2906 Build #7523 on HEAD `cb8360c04ed137bc96803f33faf3f98457f4f562` built HarfBuzz and ran all 59 upstream test groups.
- 56 groups passed, 1 was skipped by the upstream rule, and `check-static-inits` / `check-symbols` failed before inspection because OHOS Python attempted to launch bare `llvm-objdump` / `llvm-nm` names.
- The Worker exported those names and included the LLVM tool directory in `PATH`; successful Autotools builds on the same Worker also exercised them. The failure was command resolution in Python `posix_spawn`, not a missing HarfBuzz artifact or a test assertion.
- The recipe resolves the tools to executable absolute paths before `meson.test()`. Build #7546 passed all seven CI steps on follow-up HEAD `636741ba00a19aa07b87af58309a67603ddf7f67`.
- Initial AI Review follow-up: a partially allocated `hb_buffer_t` is destroyed before the consumer test returns, and signing tools no longer depend on fixed Worker paths.
- Second AI Review follow-up: archive tools now use the same resolver as test/signing tools, so version suffix handling cannot diverge between `generate()` and `_resolve_tool()`.
- Build #7584 passed all seven CI steps on follow-up HEAD `6de3ea24626b8b0b00feebd494289aa8e039fa23`.
- Third AI Review follow-up: `llvm-objcopy`, `binary-sign-tool`, and shared-library paths are emitted with `shlex.join()`, preserving each dynamic path as one shell argument. Formal CI must be repeated after this change is pushed.

---

**编译结束**: 2026-07-18 03:07
**最终状态**: built
