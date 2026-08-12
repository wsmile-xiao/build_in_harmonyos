# ncurses 6.4 适配笔记

## Baseline

- Official stable release: 6.4, 2022-12-31
- Source URL: https://ftp.gnu.org/gnu/ncurses/ncurses-6.4.tar.gz
- Source SHA-256: `6931283d9ac87c5073f30b6290c4c75f21632bb4fc3603ac8100812bed248159`
- Build system: Autotools
- Conan reference: `ncurses/6.4`
- Third-party Conan prerequisites: none
- Final state: `built`

## Package contract

- Build static wide-character libraries only (R4/R26). Shared ncurses libraries
  can shadow the platform `libncursesw.so.6` and crash the system zsh.
- Install public headers at the top-level include directory, all four static
  library components, the 11 command-line tools, and the complete terminfo database.

## Adaptation

1. `0001-port-for-ohos.patch` — config.guess + config.sub add HarmonyOS detection,
   returning `aarch64-unknown-linux-ohos` without `--build`/`--host`/`--target`.
2. `0002-fix-expr-and-umask.patch` — two fixes:
   - **expr detection**: toybox `expr` (0.8.12) cannot evaluate Autoconf compound
     regex expressions, producing garbage bytes in `ac_dir`/`top_srcdir` that
     corrupt generated Makefiles. The patch changes the `as_expr` detection from
     a simple `expr a : '\(a\)'` test to a compound-regex test
     `expr Xdir/file : 'X\(.*[^/]\)//*[^/][^/]*/\*$' \| . : '\(.\)'` that returns
     `dir` only if expr handles compound patterns. On toybox this returns empty,
     so `as_expr=false` and configure falls back to the sed-based path computation.
   - **umask 077**: `config.status` creates temporary directories with
     `(umask 077 && mktemp -d -q ...)` which on HMDFS produces directories that
     cannot be written to (Permission denied). The patch removes `umask 077` from
     both the mktemp and mkdir fallback paths in `configure`.
3. GNU coreutils (9.10) installed via cmd-pkgs provides a working `expr` in the
   local build environment; the 0002 patch makes the recipe robust even when
   only toybox is available.
4. `ac_cv_func_setfsuid=no` is set in the OHOS build environment to prevent the
   configure probe from executing unsupported syscall 151.

## Build configuration

```
CC=clang CFLAGS="-fPIC -O2" ./configure \
  --prefix=/ \
  --disable-shared --enable-static \
  --without-shared --without-debug \
  --without-ada --without-manpages --without-tests --without-cxx-binding \
  --enable-widec --enable-overwrite
make -j1 SHELL=/bin/sh
make -j1 SHELL=/bin/sh check
make -j1 SHELL=/bin/sh DESTDIR=$stage install
```

## Build results

- 4 static libraries: libncursesw.a (732KB), libpanelw.a (22KB), libmenuw.a (57KB), libformw.a (122KB)
- 11 command-line tools: clear tput tic infocmp toe captoinfo infotocap reset tabs tset ncursesw6-config
- 2851 terminfo entries
- 13 public headers (curses.h, term.h, panel.h, menu.h, form.h, etc.)
- 0 shared libraries (verified: no .so files in package)

## Test results

- `make check`: "The test-programs are interactive" (--without-tests skips test compilation)
- R7 safety scan: 10 binary tools show "Operation not permitted" (unsigned ELF, platform
  limitation — CI signs via sign.sh); ncursesw6-config (shell script) runs and reports 6.4.20221231
- L1 smoke test: links static ncursesw, verifies curses_version() == "6.4.*", setupterm + tputs

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 手动下载 (init-build 超时, /tmp 只读用 $TMPDIR) |
| Step 2 patches | ✅ | 0001 config.guess + 0002 expr/umask |
| Step 3 configure | ✅ | GNU coreutils expr 修复后通过 |
| Step 4 make | ✅ | make -j1, 零错误 |
| Step 5 install | ✅ | 2851 terminfo, 4 静态库, 11 工具 |
| Step 6 safety | ✅ | R7 扫描: 二进制未签名 (平台限制), 脚本可执行 |
| Step 7 check | ✅ | "test-programs are interactive" |
| Step 8 staging | ✅ | 4 lib + 11 bin + 13 include + 0 .so |
| Step 9 conan-init | ✅ | conanfile.py + conandata.yml + test_package/ |
| Step 10 conan-verify | ✅ | 8 门禁通过 |
| Step 11 finish | ✅ | published |

**编译结束**: 2026-08-11
**最终状态**: built
---

**编译结束**: 2026-08-11 13:46
**最终状态**: built
