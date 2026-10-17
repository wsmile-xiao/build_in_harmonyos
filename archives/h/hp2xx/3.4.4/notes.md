# hp2xx 3.4.4 HarmonyOS Adaptation Notes

## Status

- Branch: `feat/hp2xx-3.4.4`
- Issue: #1622.
- Scope: `archives/h/hp2xx/3.4.4/` plus software-level
  `archives/h/hp2xx/commands.json`.

## W0 Dependency Check

The selected package profile has no required Conan dependencies.

Upstream `sources/Makefile` enables X11 preview plus PNG/TIFF/JPEG support by
default. Those are optional features and were intentionally disabled for this
PR by building with:

- `PREVIEWER=no_prev`
- `DEFINES=-DUNIX`
- empty `EX_SRC`, `EX_OBJ`, `EX_DEFS`, `EX_LIBS`
- `ALL_LIBS=-lm`

This avoids mixing X11/libpng/zlib/libtiff/libjpeg/pdflib/libEMF/freetype
adaptation work into the hp2xx PR.

## Source And Build System

- Source: https://ftp.gnu.org/gnu/hp2xx/hp2xx-3.4.4.tar.gz
- SHA256: `47b72fb386a189b52f07e31e424c038954c4e0ce405803841bed742bab488817`
- Build system: old hand-edited Makefile under `sources/`
- Install strategy: manual copy of `sources/hp2xx` and `doc/hp2xx.1`

## Patches

- `0001-fix-minimal-ohos-build.patch`
  - Adds `string.h` for the non-GNU branch of the bundled old `getopt.c`.
  - Uses a `TMPDIR`-aware `mkstemp` temporary file path when
    `HP2XX_USE_MKSTEMP` is enabled; OHOS rejected the libc `tmpfile()`
    default path during SVG smoke conversion.
  - Makes `no_prev.c` return `int` to match the existing prototype.

## Verification

Local front-work verification on Windows host:

- Downloaded GNU source tarball and verified SHA256.
- Inspected upstream build system and optional dependency toggles.
- Direct MinGW GCC smoke build of the same minimal source set succeeded.
- Ran the locally built binary:
  - `hp2xx --version`
  - `hp2xx -m svg -f smoke hp-tests/colors.hp`
  - `hp2xx -m pbm -f smoke-pbm hp-tests/colors.hp`
- OHOS single-package `ci/conan/build_and_test.sh archives/h/hp2xx/3.4.4`
  passed on 2026-07-30:
  - L0: pass
  - L1: pass, `test_package` executed
  - L2: pass, `hp2xx --version`
  - L4: pass, patches clean
  - L5: pass, `bin/` has content

During OHOS validation, the first run failed at recipe smoke conversion because
`tmpfile()` opened an unwritable default path. The patch now uses `mkstemp`
with `TMPDIR` fallback. A later run exposed that `test_package` executes from
its build folder, so it now invokes `test.sh` via `self.recipe_folder`.

Not run yet:

- PR shadow job after issue/branch publication, if required by project process.

## Next Commands

Device/shadow CI should be queued as a single package:

```sh
CI_PACKAGES="archives/h/hp2xx/3.4.4" zsh ci/conan/build_and_test.sh
```

If using the shadow runner:

```sh
/path/to/run-ohos-shadow-ci.sh archives/h/hp2xx/3.4.4
```
