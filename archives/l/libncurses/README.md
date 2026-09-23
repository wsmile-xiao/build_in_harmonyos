# libncurses

Narrow-character (8-bit) ncurses libraries and terminal utilities for HarmonyOS PC.

This archive packages the **non-wide** ncurses ABI. The wide-character variant of the
same upstream release is tracked separately as `archives/n/ncurses/6.6`. Keeping the
narrow ABI in its own Conan package lets consumers that only need 8-bit cells link
`libncurses.a` without pulling the wide shared library that the platform shell depends on.

## Version

- `6.6_p20260516`: ncurses 6.6 (upstream release 2025-12-30), packaged as
  `libncurses/6.6_p20260516`.
- Source: https://invisible-mirror.net/archives/ncurses/ncurses-6.6.tar.gz
- SHA-256: `355b4cbbed880b0381a04c46617b7656e362585d52e9cf84a67e2009b749ff11`

## Build contract

- Autotools build with `--disable-widec`, `--without-shared`, `--enable-overwrite`
  and `--enable-pc-files`; static archives only.
- Shared ncurses libraries are rejected by the recipe. A shared
  `libncurses.so.6`/`libtinfo.so.6` shipped by a package can shadow the platform
  terminal library and break `/bin/zsh`.
- The package installs `curses.h` at the top-level `include` directory, the
  `libncurses.a`/`libform.a`/`libmenu.a`/`libpanel.a`/`libncurses++.a` archives,
  the terminal utilities and the complete terminfo database.
- Consumers get relocatable `ncurses6-config` and pkg-config metadata
  (`ncurses`, `form`, `menu`, `panel`, `ncurses++`).

## Verification

The upstream `make -j1 check` target is executed inside `conan build`, and the
`test_package` consumers cover the Conan CMake config, the upstream CMake
`FindCurses` module, the generated `ncurses6-config` script, all five pkg-config
modules and a HarmonyOS-specific static-linkage contract. Details and measured
results are recorded in [the version notes](6.6_p20260516/notes.md) and
[the test report](6.6_p20260516/reports/test-report.md).
