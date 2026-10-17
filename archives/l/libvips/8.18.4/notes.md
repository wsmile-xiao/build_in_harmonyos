# libvips 8.18.4 adaptation notes

## Scope

libvips is a demand-driven, horizontally threaded image processing library
used as the engine of `sharp`, `ruby-vips`, and the `vips` CLI. This package
builds the core `libvips` C library for OHOS AArch64 via Meson.

The dependency surface is intentionally narrowed to libraries already adapted
for OHOS in this repository:

- glib/2.88.3 (core object/IO/threading, also provides gio/gobject)
- expat/2.8.2.1 (SVG/XML text loader)
- zlib/1.3.2 (PNG zlib backing)
- lcms2/2.19 (colour management)
- libpng/1.6.58.2 (PNG load/save)
- libexif/0.6.26.1 (EXIF metadata)
- orc/0.4.42 (SIMD inner-loop code generation)

All other optional loaders are disabled (`jpeg`, `webp`, `tiff`, `heif`,
`fftw`, `rsvg`, `magick`, `openslide`, `matio`, `openexr`, `openjpeg`,
`poppler`, `pdfium`, `archive`, `highway`, `raw`, `spng`, `uhdr`, `cgif`,
`cfitsio`, `fontconfig`, `pangocairo`, `imagequant`, `quantizr`, `jpeg-xl`,
`nifti`, `giflib`-style extras). `modules`, `introspection`, `vapi`,
`examples`, `docs`, and `cplusplus` are disabled so the package is a focused
runtime-library surface.

## Build adaptations

- Meson `subdir('test')` and `subdir('fuzz')` are removed from `meson.build`.
  The upstream `test/` directory references a Python interpreter and a
  git-submodule image fixture tree that is absent from the release tarball,
  and `fuzz/` requires libFuzzer/oss-fuzz harnesses. Removing them keeps the
  cross build hermetic (a dependency-chain reviewer note: the same approach is
  used by the conan-center-index recipe).
- OHOS uses a clang-based cross toolchain; the recipe resolves `llvm-ar`,
  `llvm-ranlib`, `llvm-nm`, `llvm-objcopy`, `llvm-strip` beside the configured
  C compiler (same `_resolve_llvm_tools` approach as glib/2.88.3) and passes
  them to the Meson cross/native toolchain.
- `--wrap-mode=nofallback` keeps the build from silently fetching Meson wraps.
- Build/install run with `TMPDIR` pointed inside the build tree for OHOS.

## Test coverage

Upstream registers 24 tests when the test subdirectory is enabled: 11 Meson
tests (six shell scripts `cli`, `formats`, `seq`, `stall`, `threading`,
`keep`; five C programs `token`, `connections`, `descriptors`,
`webpsave_timeout`, `gifsave_timeout`) plus 13 pytest modules in
`test-suite/` (arithmetic, colour, connection, conversion, convolution,
create, draw, foreign, histogram, iofuncs, morphology, mosaicing,
resample).

Of those, 6 are runnable on the packaged OHOS build and are vendored into the
test_package and executed on the native OHOS CI worker:

- C tests vendored byte-for-byte from `test/` of the 8.18.4 release archive:
  `test_descriptors.c` (file-descriptor closure on minimise/read/unref; 0
  pass / 77 skip / 1 fail), `test_connections.c` (custom `VipsSourceCustom`
  load + `VipsTargetCustom` save over the enabled `pngload_source` path, no
  jpeg involved), and `test_token.c` (seven `vips__token_get` parsing
  checks driven by the vendored `test_token.sh` wrapper).
- Shell tests whose bodies match upstream `test/{cli,seq,threading}.sh` and
  which are made self-sufficient: they source a vendored `variables.sh`
  (tools resolved from PATH, seed image via `TEST_IMAGE`, `bc` replaced by
  exact integer-part comparisons) instead of Meson `@abs_top_builddir@`
  substitution. `test_cli.sh` writes thumbnails to `.png` instead of `.jpg`
  because jpeg save is disabled; the size/geometry assertions are unchanged.

The 18 non-runnable upstream tests are reported as such: the 13 pytest
modules need a Python interpreter and the `test-suite/images` git submodule
(absent from the release tarball); `formats`/`stall`/`keep` need loaders and
image fixtures this package does not ship; `webpsave_timeout` and
`gifsave_timeout` need webp/gif save support that is disabled.

The test_package:
- compiles and runs a consumer test (`test_vips.c`) that exercises
  `VIPS_INIT`, runtime version reporting, `vips_black`, `vips_avg`,
  `vips_add`, `vips_pngsave_buffer`, and `vips_pngload_buffer` with six
  PASS/FAIL assertions. `--gen-image` materialises a 64x64 black PNG at
  runtime for the vendored C tests (test_descriptors reads 10-row crops at
  y=0/y=20, so the fixture must be taller than 30 rows).
- registers four ctest cases: `vips_consumer`, `gen_png`,
  `upstream_descriptors`, `upstream_connections`.
- runs the vendored shell tests (`test_token.sh`, `test_cli.sh`,
  `test_seq.sh`, `test_threading.sh`) through bash on OHOS.
- needs the packaged CLI tools to be executable inside the OHOS sandbox:
  the recipe mirrors `vips`/`vipsheader`/`vipsthumbnail` (and `libvips.so`)
  from the conan cache into the exec-allowed build folder, then strips and
  re-signs them plus the CMake-built test binaries with `binary-sign-tool`
  (same pattern as the libevent test_package). The upstream `sample.png`
  seed (290x442, identical geometry to the `sample.jpg` the scripts were
  written for) is not committed to the PR: the CI pre-flight applies the PR
  as a git patch that cannot carry new binaries, so the test_package
  synthesises an equivalent black RGB seed at build time with the packaged
  `vips black <seed> 290 442 --bands 3` CLI and exports it as `TEST_IMAGE`.

On the OHOS cross build (`can_run` unavailable) the test binaries are
compiled and linked but execution is skipped with an explicit log line, the
same convention used by other Meson packages in this archive. Runtime
execution happens on the native OHOS CI worker (profile `ohos-aarch64`).

## Local validation

- Python syntax check passed for the recipe and the test recipe.
- `git diff --check` passed.
- Official source archive SHA256 verified:
  `2677bad6c422617fd1172d359c16af34e736965d042c214203a87187d26ff037`
  (libvips-8.18.4.tar.xz from the GitHub release).
- Meson option names and feature/boolean types cross-checked against
  `meson_options.txt` for every project option set in `generate()`.
- pkg-config names of all dependencies cross-checked against the Meson
  `dependency()` calls in `meson.build` (glib-2.0/gio-2.0/gobject-2.0,
  expat, zlib, libexif, lcms2, libpng, orc-0.4).
- CMakeDeps/CMakeToolchain consumer (`test_package`) configure/compile
  checked against the vips::vips CMake target naming.
- Vendored C tests verified byte-identical to the upstream release archive
  (SHA-256); the shell-test seed is generated at runtime as a 290x442 black
  RGB PNG (geometry matches the upstream `test-suite/images/sample.png`).
- CI #37420 (OpenHarmonyPCDeveloper-CI-001): `conan create` + `ctest` 4/4 +
  the six vendored upstream tests all passed; L0/L1 gates green.

Remaining limitation: 18 of the 24 upstream tests are not runnable on the
packaged configuration (Python + `test-suite/images` submodule for pytest,
disabled webp/gif and other loaders for `formats`/`stall`/`keep` and the two
`*_timeout` tests); the 6 runnable Meson tests are vendored and executed, and
the six-check consumer test covers the packaged runtime surface.
