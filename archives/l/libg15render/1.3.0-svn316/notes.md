# libg15render 1.3.0-svn316 adaptation notes

## Build environment

- Target: HarmonyOS/OHOS 6.0, AArch64, musl
- Compiler: profile-selected Clang 15.0.4
- Build system: direct C compilation driven by Conan
- Dependency: `freetype/2.14.3`
- Status: built

## Build approach

The official SVN r316 snapshot contains Autotools input files but no generated `configure` script. Its `configure.in` invokes the obsolete `freetype-config` helper. Rather than regenerate an old Libtool stack and introduce a compatibility shim, the recipe compiles the complete three-source library and `g15fontconvert` directly. Compiler paths come from `tools.build:compiler_executables`; FreeType include and library paths come from the Conan dependency.

The package preserves the upstream Libtool ABI naming (`libg15render.so.1.1.0`, SONAME `libg15render.so.1`) and supports the standard Conan `shared` option. It installs the public header, all 40 bitmap fonts, manual page, license, pkg-config metadata and font converter.

## Issues and solutions

| # | Issue | Root cause | Solution |
|---|-------|------------|----------|
| 1 | `freetype-config` is unavailable | FreeType removed the legacy helper and the OHOS package exposes standard include/lib metadata | Read include and library directories from `freetype/2.14.3` through Conan |
| 2 | Modern C compilation lacks declarations in several source files | The 2009 sources relied on indirect standard-library declarations | Add explicit `stdio.h`, `stdlib.h`, `string.h` and `strings.h` includes |
| 3 | Default bitmap fonts are not relocatable | Upstream embeds `${prefix}/share/g15tools/fonts` at compile time | Honor `LIBG15RENDER_FONT_DIR`, retaining the upstream path as fallback |
| 4 | Missing or short WBMP inputs can dereference invalid data | The loader treated fd `-1` as success and the splash helper did not check a null result | Validate the file descriptor/read length, close failure paths, check null and release loaded data |
| 5 | `g15r_ttfLoad()` can dereference an invalid face after canvas initialization | `g15r_initCanvas()` left the FreeType face and size arrays uninitialized | Clear the complete `g15canvas` structure before initializing FreeType |
| 6 | Package-tool validation needs deterministic version discovery | The historical converter implements help but no version query | Add `-V`/`--version` using the configured package version |
| 7 | SourceForge snapshot URL returns 404 after local verification | `code-snapshots` archives are generated on demand and removed after a short retention period | Use Launchpad's immutable archive of the same SVN r316 upstream source and verify every source file matches |

## Upstream test audit

- Archive contents: four C source files (`text.c`, `pixel.c`, `screen.c`, `g15fontconvert.c`), Autotools inputs, 40 fonts and documentation.
- No `tests/` or `test/` directory exists; no source filename contains `test` or `check`.
- `Makefile.am` and `src/Makefile.am` contain no `TESTS`, `check_PROGRAMS`, `check_LTLIBRARIES`, `check-local` or test target.
- The only `make check` text is generic boilerplate in `INSTALL`; no such target is defined.
- Upstream discovered/executed/passed: 0/0/0. No upstream test was modified or omitted.

## Added verification

- `test_libg15render.c`: 15 cases covering core pixels, modes, drawing primitives, XBM, packaged fonts, bitmap text, FreeType and WBMP error paths.
- `test_libg15render_ohos.c`: 3 HarmonyOS-specific checks for `__OHOS__`, AArch64/64-bit ABI and a real boundary pixel operation.
- Packaged `g15fontconvert --help` and `--version`: 2 executable integration checks.
- Added tests: 20/20 passed on the HarmonyOS PC target.

## Patch inventory

- `0001-src-g15fontconvert.c.patch`: explicit standard declarations and CLI version discovery.
- `0002-src-pixel.c.patch`: safe WBMP error handling and buffer release.
- `0003-src-screen.c.patch`: complete canvas initialization and explicit `printf` declaration.
- `0004-src-text.c.patch`: allocation declaration and relocatable font lookup.

All patches are portable C fixes and introduce no platform macro or stub.

## Verification commands

```text
conan create archives/l/libg15render/1.3.0-svn316 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
```

Expected result: library and tool build successfully; upstream status is `no_tests`; consumer tests report 20/20 passed.

---

**编译结束**: 2026-09-20
**最终状态**: built
