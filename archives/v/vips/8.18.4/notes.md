# vips 8.18.4 W0 adaptation notes

Issue: 1909
Branch: feat/vips-8.18.4-1909
Archive path: archives/v/vips/8.18.4

## Scope

The user-facing target name was libvips. The repository already tracks this
project under archives/v/vips, with prior 8.14.1 and 8.18.2 notes, so this pass
adds version 8.18.4 under the existing canonical package directory.

This is a W0/front-load adaptation. It prepares the source metadata, Conan
recipe, and non-empty test_package. An official PR CI attempt showed that the
temporary follow-up dependency versions from expat issue #1912 and pcre2 issue
#1913 were not yet published, so the release-facing recipe now avoids those
unpublished coordinates.

## Source

- URL: https://github.com/libvips/libvips/releases/download/v8.18.4/vips-8.18.4.tar.xz
- sha256: 2677bad6c422617fd1172d359c16af34e736965d042c214203a87187d26ff037
- Build system: Meson

GitHub download failed from this local host. SourceForge's small sha256sum file
was reachable and provided the checksum. Large source downloads from the mirror
were slow/truncated locally, but the partial tarball exposed the top-level Meson
files needed for source analysis.

## Dependencies

Core required dependencies identified from meson.build:

- glib2/2.88.0 for glib-2.0, gio-2.0, and gobject-2.0
- expat/2.8.2.1 for XML support
- pcre2/10.45 through glib2's published transitive dependency
- system threads and libm

Conan remote W0 download checks were not executed on the Windows host because
conan is not available in this PATH. The release-facing recipe uses the
repository's existing expat/2.8.2.1 recipe and does not override glib2's pcre2
dependency, avoiding unpublished expat/2.8.2.1.1 and pcre2/10.45.1.1
coordinates in official PR CI.

## Build strategy

The recipe starts with a minimal core build:

- Meson default_library follows the Conan shared option, defaulting to static.
- modules, introspection, vapi, docs, C++ binding, C++ docs, and examples are
  disabled.
- Optional codec and document backends are disabled: archive, cfitsio, cgif,
  exif, fftw, fontconfig, heif, highway, imagequant, jpeg, jpeg-xl, lcms,
  magick, matio, nifti, openexr, openjpeg, openslide, orc, pangocairo, pdfium,
  png, poppler, quantizr, raw, rsvg, spng, tiff, uhdr, webp, and zlib.

This avoids pulling unpublished or unverified optional dependency adaptations
into the vips PR.

## Test package

test_package/test.c initializes libvips, creates a 2x2 matrix image with values
1, 2, 3, and 4, calls vips_avg(), and asserts the average is 2.5. This provides
a consumer-level C API and link validation without image codec dependencies.

## Deferred validation

Device shadow CI was attempted on 2026-08-07 via:

```sh
sh "$HOME/ohos-users/codex/vips-8.18.4-1909-shadow-20260807/run-conan-heavy.sh"
```

Results:

- Run `codex-8.18.4-vips-8.18.4-1909-shadow-20260807-conan-20260807-111733-20297`
  failed during dependency graph resolution for the initial `glib2/2.88.0` and
  `expat/2.8.2.1` requirements because the device job was created from an older
  repository snapshot that did not contain those recipes.
- Run `codex-8.18.4-vips-8.18.4-1909-shadow-20260807-conan-20260807-112429-23244`
  used `glib/2.84.0` and `expat/2.8.2`, but failed before build because
  `glib/2.84.0` is neither published nor available as a local Conan recipe in
  the device CI snapshot.
- A fresh current-main based job
  `vips-8.18.4-1909-fresh-20260807` applied this vips patch cleanly. After
  manually exporting the transitive `pcre2/10.45` and `zlib/1.3.1` recipes into
  the isolated Conan cache, run
  `codex-8.18.4-vips-8.18.4-1909-fresh-20260807-conan-20260807-114632-32670`
  reached dependency build, but failed before compiling vips when
  `expat/2.8.2.1` could not create the `libexpat.so.1` and `libexpat.so`
  symlinks on the device filesystem:
  `CMake Error: failed to create symbolic link 'libexpat.so.1': Permission denied`.
- A verification-only overlay job
  `vips-8.18.4-1909-with-expat1912-20260807` applied the expat issue #1912 fix
  first, then this vips patch. Run
  `codex-8.18.4-vips-8.18.4-1909-with-expat1912-20260807-conan-20260807-123027-60132`
  confirmed that expat now builds, installs, signs, and packages as
  `libexpat.so` without the previous symlink failure. The next dependency
  blocker is `pcre2/10.45`, which fails before vips is compiled:
  `/system/bin/sh: .../pcre2.../configure: Permission denied`.

Per the one-library-one-PR rule, do not change expat, glib2, pcre2, or zlib in
this vips PR.

Follow-up shadow CI after expat issue #1912 and pcre2 issue #1913 were staged:

- Job directory:
  `/storage/Users/currentUser/ohos-users/codex/vips-8.18.4-1909-with-expat1912-20260807`
- Runner directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-8.18.4-vips-8.18.4-1909-with-expat1912-pcre21913-r8-20260807-conan-20260807-155851-60776`
- Result: `rc=0`; L0 pass, L1 pass, L4 pass, L5 pass.
- Non-blocking warning: L2 skipped because installed CLI `--version/--help`
  checks returned non-zero for `vips`, `vipsedit`, `vipsheader`, and
  `vipsthumbnail`.
- Test evidence: `conan create` built `vips/8.18.4`, packaged `libvips.a`, four
  CLI tools, headers, pkg-config metadata, and executed `test_package` via
  `./test_vips`.
- R34 evidence: destructive negative test moved `bin/`, `lib/`, and `include/`
  away and confirmed the test genuinely depends on `vips`.

Official PR CI attempt #15549 failed because the recipe still referenced
unpublished expat/2.8.2.1.1 and pcre2/10.45.1.1 coordinates. The recipe was
updated to use expat/2.8.2.1 directly and to let glib2 keep its pcre2/10.45
transitive dependency.

Run only the target package in CI/shadow CI:

```sh
CI_PACKAGES="archives/v/vips/8.18.4" zsh ci/conan/build_and_test.sh
```

Shadow CI command:

```sh
/path/to/run-ohos-shadow-ci.sh archives/v/vips/8.18.4
```

After dependency publishing is confirmed, optional image backends can be restored
one by one in separate, evidence-backed follow-up work.
