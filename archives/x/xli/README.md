# xli

`xli` is an X11 image display and manipulation utility, a long-lived fork of
`xloadimage` with added JPEG/PNG support. It can display images on an X11
display, convert between image formats, and set the root window background.
The package ships two programs: `xli` (needs an X display) and `xlito` (same
options, works without a display, e.g. for conversions and root-window setup).

## Package contents

- Command-line tools: `xli` and `xlito` (under `bin/`)
- Manual pages: `xli.man`, `xlito.man` (under `share/man/man1`)
- License: MIT
- Runtime dependencies: `libx11`, `libxext`, `libjpeg`, `libpng`, `zlib`

## OpenHarmony adaptation

- Upstream ships an `Imakefile`; the OHOS SDK provides neither `imake` nor
  `xmkmf`, so the build uses the `Makefile.std` that the release tarball
  already contains (the documented non-imake path). Include/library flags are
  injected from the Conan dependency graph instead of imake's `-I`/`-L`
  resolution, and the compiler comes from the Conan toolchain.
- OHOS (musl) libc does not provide the BSD legacy symbol `rindex()`
  (`index`, `bcopy`, `bzero`, `bcmp` are present). A minimal per-function
  replacement `-Drindex=strrchr` is used on the command line; the upstream
  `-DSYSV` switch is deliberately *not* enabled because it pulls in further
  SysV-only features (`F_FREESP`, `stropts.h`, `poll.h`) that musl lacks too.
- The `Makefile.std` install target only installs `xli`; the recipe also
  copies `xlito` and the man pages into the package.
- Upstream has no test suite, so the recipe is verified by `test_package`,
  which exercises `xlito` (round-trip format conversion) plus an `xli`
  startup smoke check.
- R40 note: CI has no X display, so the graphics path is covered at
  startup/option-parsing level only; pixel-level rendering against a real
  X server remains a manual confirmation item on device.
- The upstream project site is offline (HTTP 404); the source is the openSUSE
  fork snapshot of the 2006-11-10 release, pinned by `sha256` in
  `conandata.yml`.

## Usage

```bash
# Conan sets bindirs/runenv; xli needs an X display
xli photo.png

# Conversion / no-display operation via xlito (same options as xli)
xlito -dump photo.png > photo.ppm
```
