# libnewt

Newt (Not Erik's Windowing Toolkit) is a C library for color text-mode,
widget-based user interfaces: stacked windows, entries, checkboxes, radio
buttons, labels, text fields, scrollbars and dialog boxes. It is built on the
S-Lang library; the same source tree also builds the `whiptail` shell-dialog
utility (popt-based).

## OHOS adaptation

- Configure script is hand-written (not automake): no `config.guess`/`config.sub`,
  so there is no HarmonyOS system-identification issue.
- `Makefile.in` has no VPATH support: the recipe syncs the sources into the
  build folder and configures/makes in-tree.
- OHOS builds use `--without-python --without-tcl --disable-nls` (no python
  dev headers, no tclConfig.sh, no libintl on device).
- `make GNU_LD=ld` forces the `-soname/--version-script` branch so
  `libnewt.so` carries a proper `DT_SONAME`.
- OHOS has no standalone `install(1)`; the recipe ships a minimal
  `.hmbs-bin/install` shim used only at install time.
- Upstream ships no automated test suite (interactive TTY demos only), so
  verification is consumer-side: link + palette/macro checks and
  `whiptail --version`.

## Dependencies

- slang 2.3.3 (S-Lang)
- popt 1.16

## References

- https://pagure.io/newt
- https://releases.pagure.org/newt/
- https://www.linuxfromscratch.org/blfs/view/stable-systemd/general/newt.html
