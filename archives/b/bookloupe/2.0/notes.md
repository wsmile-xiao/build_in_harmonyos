# bookloupe 2.0 — HarmonyOS PC (aarch64) adaptation notes

## Summary

bookloupe checks Project Gutenberg(TM) candidate e-texts for common formatting
errors.  C program, autotools build, GLib >= 2.18 dependency.

- Upstream: http://www.juiblex.co.uk/pgdp/bookloupe/ (http only, no https)
- License: GPL-2.0-only
- Conan ref: `bookloupe/2.0`（上游唯一正式发布版；源码为上游官方 bookloupe-2.0 tarball。注：平台任务曾按 "2"/分支 `feat/bookloupe-2` 出题，但 Conan 版本号长度 ≥2 限制与 CI 分支=版本一致约束使其无法通过，已按 2.0 提交并反馈平台修正）
- Directory: `archives/b/bookloupe/2.0`

## Build

Standard autotools (configure + make) cross-compiled for
`aarch64-linux-ohos` with clang 15 (OHOS-adapted Conan profile,
host=OHOS/armv8).  Dependency: `glib/2.88.0.1` (published static binaries for
armv8/clang15/OHOS are reused).

Key points:

1. GLib discovery: configure uses `PKG_CHECK_MODULES([GLIB],[glib-2.0 >=
   2.18])`.  `PkgConfigDeps` generates `glib-2.0.pc` (+ pcre2) and the
   toolchain env points `PKG_CONFIG_PATH` at the generator folder.
2. The tarball's `config/` aux scripts date from ~2009 and `config.sub` has no
   aarch64 support.  `patches/config-sub-aarch64.patch` adds `aarch64` /
   `aarch64-*` to its CPU match lists (a minimal, surgical change).  Configure
   is invoked with `--host=aarch64-linux` (add `--build=aarch64-linux` when
   building natively) so autoconf never has to guess the OHOS triple.
3. Upstream regression tests (`make check`): 37 `.tst` cases in
   `test/compatibility` (35) and `test/bookloupe` (2), driven by the
   `loupe-test` harness (in `test/harness`).  They are executed only when
   `can_run(self)` is true (native OHOS worker / device).
4. Runtime data: `bookloupe` looks for `bookloupe.typ` in CWD and then in the
   executable's directory.  The package installs `bin/bookloupe` and a copy of
   `bin/bookloupe.typ`, making the tool self-contained.
5. On OHOS workers the ELF is signed with `/data/service/hnp/bin/
   binary-sign-tool` (mirrors boxshade/glib recipes).
6. OHOS HMDFS config.status issue (E114): config.status creates its
   `./confXXXXXX` temp dir with `umask 077`, which on HMDFS yields a
   `drwx--S---` directory not writable by its owner → `subs1.awk: Permission
   denied`.  `patches/configure-umask.patch` relaxes the two `umask 077` in
   `configure` to `umask 022`.
7. glib ≥ 2.30 provides `g_mkdtemp`; the autoconf `AC_CHECK_FUNCS` link probe
   can spuriously fail against the *static* glib archive (would make
   `bl/mkdtemp.c` compile its own `g_mkdtemp` → duplicate symbol vs
   `libglib-2.0.a` at final link).  The recipe pins
   `ac_cv_func_g_mkdtemp=yes ac_cv_func_mkdtemp=yes` for configure.
8. Libtool vs dependency `*.la` archives: the published pcre2 (and some other)
   Conan packages ship `libtool *.la` files whose recorded `libdir` belongs to
   the release worker; libtool on the device worker then fails with
   "library `...la` was moved / not a valid libtool archive".  The recipe
   deletes dependency `*.la` files from the Conan cache lib dirs before `make`
   (Conan consumers never need `.la`; e.g. a52dec strips its own).
9. pkg-config search nondeterminism: some device workers carry a leftover
   system `glib-2.0.pc` under `$HOME/usr/local`, so configure's
   `PKG_CHECK_MODULES` could pick it instead of the Conan-generated .pc
   (flags without `-lintl`) → static link then failed on missing
   `g_libintl_*`.  The recipe passes `PKG_CONFIG_LIBDIR=<generators_folder>`
   to disable system search dirs and make GLIB_CFLAGS/GLIB_LIBS deterministic.
10. Cross-worker `g_libintl_*` link nondeterminism: even with the .pc fixed,
    some workers ended up linking glib without its bundled `libintl.a`
    (`undefined symbol: g_libintl_*` from ggettext.o).  The recipe injects a
    small C object with **weak** no-op definitions of all `g_libintl_*`
    functions into the executable link lines (LIBS in bookloupe/Makefile and
    test/harness/Makefile); a strong libintl.a overrides them when present, so
    the link is deterministic on every worker.

## Caveats / porting observations

- No changes to upstream C sources were needed; only the build-aux
  `config.sub` was refreshed (portability).
- Source download uses plain `http` — the upstream site has no https endpoint
  (Homebrew deprecates the formula for the same reason).
- `bookloupe --version`/`--help` exit with status 1 by design (GOption parse
  failure path prints help then exits 1), so CI smoke covers running it on a
  file rather than `--help`.
