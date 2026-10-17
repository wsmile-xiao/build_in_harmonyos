# wev

Wayland event viewer.

## Description
`wev` ("xev for Wayland") opens a surface and prints every `wl_*` event it
receives — keyboard, pointer, touch and tablet events — which makes it the
quickest way to verify that a compositor session and input devices work.

## Homepage
https://git.sr.ht/~sircmpwn/wev

## License
MIT

## Build System
Plain Makefile (upstream ships no configure/cmake/meson); every knob is read
through `pkg-config`.

## Dependencies
- wayland/1.24.0 (wayland-client + wayland-scanner)
- libxkbcommon/1.13.1
- libffi/3.4.4 (wayland-client.pc `Requires.private`)
- wayland-protocols/1.47 (xdg-shell / tablet protocol XML)
- scdoc/1.11.0 (generates wev.1)
- pkgconf/3.0.6

## OHOS adaptation
No source patch. `generate()` prepares a private toolchain view for the
Makefile:

- every dependency `.pc` is copied into `fixed_pkgconfig/` with its prefix
  rewritten to the real package folder (registry `.pc` files point at the
  release worker's build cache);
- the packaged `wayland-scanner` is copied out and signed before use — an
  unsigned ELF cannot be executed on HMDFS (E077);
- `scdoc.pc` and `wayland-scanner.pc` are synthesised (upstream scdoc installs
  no `.pc`), and `pkgconf` is exposed as `pkg-config`.

## Versions
- 1.1.0: initial adaptation, Makefile build, test_package runs the shipped
  binary (usage path + no-display failure path + dynamic-link check)
  (2026-09-25)
