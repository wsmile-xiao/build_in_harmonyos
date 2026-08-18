# acedb 4.9.39+dfsg.02 适配笔记

## 编译环境

- 构建系统: custom makefile (`wmake`)
- 编译日期: 2026-08-18
- 编译器: OpenHarmony clang/clang++
- 状态: built

## 编译步骤

Conan `source()` downloads the Debian source tarball, applies the five portability patches, and creates the `wmake/OHOS_4_DEF` definition. `build()` selects `ACEDB_MACHINE=OHOS_4` and builds the command-line targets with `make -j1`. `package()` copies the resulting executables into `bin/`.

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `glib.h` was unavailable | cmd-pkgs dependencies were not installed | Installed the published `glib`, `gettext`, `ncurses`, and `flex` packages before rebuilding |
| 2 | `w3rdparty/include-config` requires csh | The legacy helper assumes a host csh installation | Used `pkg-config` directly in `OHOS_4_DEF` |
| 3 | `_sys_siglist` is unavailable | OHOS libc does not expose the legacy signal table | Added an OHOS-specific signal text path |
| 4 | GTK headers were unavailable | Command-line targets included GTK-only declarations | Guarded the GTK-only section of `wh/gex.h` with `ACEDB_NO_GTK` |
| 5 | qsort declaration conflicted with the OHOS system prototype | acedb declares a non-POSIX `mysize_t` signature | Removed the obsolete custom declaration on the OHOS/Linux path |
| 6 | Legacy scripts used unavailable host interpreters | OHOS tools are under `/data/service/hnp/bin` | Updated the release helper Perl shebang |
| 7 | Legacy static linking missed libintl/curses/flex names | The old linker inputs use host library names | Added static libintl and compatibility library handling in the recipe and OHOS definition |

## 源码修改

- `w4/sigsubs.c`: use the OHOS signal fallback.
- `waql/aql_.h`: expose the parser callback declaration for the Linux-compatible build.
- `wh/gex.h`: exclude GTK-only declarations for command-line builds.
- `wh/mystdlib.h`: remove the conflicting legacy qsort declaration.
- `wtools/aceSetReleaseDir`: use the OHOS Perl interpreter path.
- `wmake/OHOS_4_DEF`: define the OHOS clang, pkg-config, linker, flex, yacc, and archive settings.

## 依赖版本

- `glib/2.88.0` from cmd-pkgs
- `gettext/0.22.5` from cmd-pkgs
- Conan requirements: `glib/2.88.0`, `gettext/0.22.5`, `ncurses/6.6`, and `readline/8.3`
- cmd-pkgs static compatibility inputs: `pcre2/10.40`, `glib/2.88.0`, `gettext/0.22.5`, `ncurses/6.4`, and `readline/8.2`
- `flex/2.6.4` from the OpenHarmony toolchain

## 验证结果

- `conan create`: passed with `ci/conan/profiles/ohos-aarch64`
- Conan verification G1/G2/G3/G4/L2/L4/L5: passed
- Local CI `setup.sh`: passed
- Local CI `build_and_test.sh`: passed
- `test_package/test.sh`: passed 18 explicit checks covering all eight packaged commands and the upstream `md5test` aggregate outputs `mddriver` and `digtest`
- The host-side upstream `make test` baseline could not start because it hard-codes `/usr/bin/perl`; the available interpreter is `/storage/Users/currentUser/usr/local/bin/perl`. This limitation is recorded in `reports/test-report.md`.

## 交付物

The Conan package is a source-built command-line application. No prebuilt binaries are committed.

## 注意事项

The package depends on the OpenHarmony cmd-pkgs runtime/toolchain environment. It is marked `built`, not `published`, because no artifact upload was performed.

## 结束

status: closed
