# tkdiff

TkDiff is a Tcl/Tk graphical front-end for comparing files and working with
several revision-control systems.

## Version

- Upstream version: 6.0
- License: GPL-2.0-or-later
- Homepage: https://sourceforge.net/projects/tkdiff/

## HarmonyOS PC Notes

- Script-only package; no native compilation is required.
- Runtime requires Tcl/Tk `wish`.
- The upstream shell trampoline shebang is adjusted from `/bin/sh` to
  `/usr/bin/env sh` because HarmonyOS PC does not provide `/bin/sh`.
