# dinotrace

Dinotrace is a graphical waveform / value-change-dump (VCD) viewer for digital
simulation traces (Verilog, VCD, VCD, .dino, Tempest, DECsim). It was written
by Wilson Snyder and is distributed by veripool. It is a classic X11
application: the whole user interface is built on the X Toolkit (Xt) and the
Motif widget set (`libXm`).

## Functionality

- Loads digital waveforms from several simulator dump formats (`.dino`,
  `.vcd`, Verilog VCD, Tempest, DECsim …).
- Graphical waveform display with cursors, grids, value search and signal
  annotation, built from Motif widgets (`XmCreateForm`, `XmCreateMainWindow`,
  `XmCreateDrawingArea`, `XmCreateScrollBar`, `XmCreateText`, menus …).
- A headless-safe `--version` / `-version` switch (prints `Dinotrace 9.4f`).

## OHOS adaptation

- `motif/2.3.8` supplies `libXm.so.4` together with `Xm/*.h` — Motif does not
  exist upstream of this repository and is a locally adapted package. The
  recipe requires it with `transitive_headers`/`transitive_libs`.
- The 2019 hand-written top-level `Makefile` compensates for the HMDFS
  `umask 077` in `configure`, and the `/bin/sh` shebangs / `SHELL` make
  variables are repointed at the OHOS shell (no source patches).
- The build is performed **in-source** (`folders.build = "."`): the top-level
  Makefile is not VPATH-capable.
- `perl` is a hard build dependency: `src/dist_date.pl` and `src/dinodoc.pl`
  generate `dist_date.h` / `dinodoc.h`.
- `make install` (which also builds the Texinfo docs) is satisfied without
  `makeinfo` by refreshing the mtimes of the shipped `dinotrace.info/.txt/.pdf`.

## OS limitation (headless)

Neither this build machine nor HarmonyOS provides an X server (or Wayland), so
any code path that reaches `XtOpenDisplay()` cannot succeed. Dinotrace prints
`Can't open display ''` and exits. Consequently only the non-GUI surface
(`--version`) can be verified on the platform; the interactive waveform GUI is
not exercisable. This is declared in `9.4f/test_package/MANIFEST.yml`.

## Dependencies

- `motif/2.3.8` — the Motif widget set (`libXm.so.4`) + `Xm/*.h` (build & run).
- `xorgproto/2025.1` — X11 protocol headers (`<X11/X.h>`, `<X11/Xfuncproto.h>`).

(`libx11`, `libxt`, `libxext`, `libsm`, `libice` are pulled transitively by
`motif`; the recipe injects their include/lib roots through the private Conan
build folder.)

## References

- https://www.veripool.org/dinotrace
- https://www.veripool.org/ftp/ (release tarballs)

## Versions

| Version | Status |
| --- | --- |
| 9.4f | built |
