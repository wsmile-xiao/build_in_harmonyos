# paps

paps — text to PostScript converter using Pango for text layout.

Reads UTF-8 text (with optional Pango markup), lays it out with Pango,
and renders through the Cairo vector backends to PostScript (default),
PDF, or SVG.

- Homepage: https://github.com/dov/paps
- License: LGPL-2.0-or-later
- Build system: meson (C++17)

## Adapted versions

| Version | Status | Notes |
|---------|--------|-------|
| 0.8.0 | built | HarmonyOS PC (aarch64, musl, clang 15.0.4) |
