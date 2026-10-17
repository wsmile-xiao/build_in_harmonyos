# libncursesw

Wide-character ncurses libraries and terminal utilities for HarmonyOS PC.

## Version

- `6.6_p20260516`: ncurses 6.6 (2025-12-30), packaged as `libncursesw/6.6_p20260516`.
- Source: https://invisible-mirror.net/archives/ncurses/ncurses-6.6.tar.gz
- SHA-256: `355b4cbbed880b0381a04c46617b7656e362585d52e9cf84a67e2009b749ff11`

The package contains static wide-character libraries, terminal commands, public
headers, and the installed terminfo database. It does not provide shared
ncurses libraries, which could shadow the platform `libncursesw.so.6`.

The independent HarmonyOS device validation and remaining CI boundary are
recorded in [the version notes](6.6_p20260516/notes.md) and
[the evidence report](6.6_p20260516/reports/knowledge-evidence.md).
