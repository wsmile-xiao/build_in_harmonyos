# twclock

twclock is a graphical world clock and CW (Morse code) station ID generator for ham radio operators, written by Ted Williams (WA0EIR). It is a classic X11 application: the entire user interface is built on the X Toolkit (Xt) and the Motif widget set (`libXm`).

## Functionality

- Shows the time in multiple call areas (time zones) simultaneously.
- Can beep or send a Morse (CW) station ID through PulseAudio.
- Configuration via the `Twclock` app-defaults resource file (timezone, CW speed/tone, alarm settings, colors, fonts).
- Desktop entry (`twclock.desktop`) and icon (`twclock.png`) for integration with desktop environments.

## OHOS adaptation

- `motif/2.3.8` supplies `libXm.so.4` together with `Xm/*.h` — Motif does not exist upstream of this repository and is a locally adapted package. The recipe requires it with `transitive_headers`/`transitive_libs`.
- Direct dependencies: `libxt/1.3.1` (X Toolkit), `libx11/1.8.13`, `pulseaudio/17.0`, `xorgproto/2025.1`. `libxpm` is deliberately **not** required (see below).
- The automake build is VPATH-capable; an out-of-source build is used (`basic_layout`).
- `PKG_CHECK_MODULES(APPDEFS, xt)` requires `libxt`'s `xt.pc`; the libxt recipe exports `pkg_config_name = "xt"`.
- `AC_FIND_MOTIF` (from `acinclude.m4`) is satisfied via `--with-motif-includes` / `--with-motif-libraries`.
- `AC_PATH_XTRA` / `AC_PATH_X` are satisfied via `--x-includes` / `--x-libraries` pointing at the packaged `libx11`.
- Cross-compile reality: the shipped `configure` runs the `AC_FUNC_MALLOC` test; the pessimistic cross default would `#define malloc` to `rpl_malloc` and break linking, so `ac_cv_func_malloc_0_nonnull=yes` is pinned.
- E011: the `umask 077` in `configure` is rewritten to `022` and the `/bin/sh` shebangs / `SHELL` make variables are repointed at the OHOS shell (no source patches).
- Packaging is an explicit `copy()` staging with loud verification: on the OHOS/HMDFS CI worker `make install` cannot be the authoritative driver (HMDFS ignores chmod, so `config/install-sh` cannot be executed), the same defect the `dinotrace` adaptation documented. An evidence-only `make install` trace is still captured, non-fatally.

## OS limitation (headless)

Neither this build machine nor HarmonyOS provides an X server (or Wayland), so any code path that reaches `XtVaOpenApplication()` cannot succeed. twclock prints `Can't open display` and exits. Consequently only the non-GUI surface (binary existence, ELF DT_NEEDED chain, app-defaults resource, man page, desktop entry, icon) can be verified on the platform; the interactive GUI is not exercisable. This is declared in `3.5/test_package/MANIFEST.yml`.

## Dependencies

- `motif/2.3.8` — the Motif widget set (`libXm.so.4`) + `Xm/*.h` (build & run).
- `libxt/1.3.1` — X Toolkit (`libXt.so.6`) + `xt.pc` (build & run).
- `libx11/1.8.13` — X11 client library (`libX11.so.6`) (build & run).
- `pulseaudio/17.0` — PulseAudio simple API (`libpulse-simple.so.0`, `libpulse.so.0`) for CW audio output (build & run).
- `xorgproto/2025.1` — X11 protocol headers (`<X11/X.h>`, `<X11/Xfuncproto.h>`).

(`libxext`, `libsm`, `libice` are pulled transitively by `motif`; the recipe injects their include/lib roots through the private Conan build folder.)

### libxpm is intentionally omitted

`libxpm/3.5.17` in the registry is built against the `libx11/6.4.0` track, while
`motif/2.3.8` forces `libx11/1.8.13`; the two tracks are mutually incompatible, so
requiring `libxpm` would force a source rebuild of `libX11` and break the graph.
XPM is used only for the window icon and `configure.ac` has a `MAKE_ICON=0`
fallback, so the package builds and runs without it — at the cost of the XPM
window icon. This is the same root cause as the `libxext/6.4.0.1` binary gap
documented in `3.5/notes.md`.

## References

- https://packages.debian.org/sid/twclock
- https://ftp.debian.org/debian/pool/main/t/twclock/ (release tarballs)

## Versions

| Version | Status |
| --- | --- |
| 3.5 | built |