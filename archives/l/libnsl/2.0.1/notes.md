# libnsl 2.0.1 - HarmonyOS PC adaptation notes

## Upstream
- Repo: https://github.com/thkukuk/libnsl
- Tag: `v2.0.1`
- Release asset: `libnsl-2.0.1.tar.xz`
- SHA256: `5c9e470b232a7acd3433491ac5221b4832f0c71318618dc6aa04dd05ffcd8fd9`
- License: LGPL-2.1-or-later
- Build system: GNU Autotools (pre-generated `configure`, no autoreconf needed)

## Dependency
- `libtirpc/1.3.7` (ohpcd), static, OHOS aarch64.
- `configure.ac`:
  `PKG_CHECK_MODULES([TIRPC], [libtirpc], [], [TIRPC_LIBS=""])`
  If `libtirpc.pc` is not found, `HAVE_TIRPC` is never defined, the whole
  `src/taddr2*.c` bodies compile out and the library degrades silently.
  `PkgConfigDeps` in `generate()` makes the Conan graph authoritative.

## Configure flags
| Flag | Reason |
|------|--------|
| `--disable-nls` | no message catalogues / msgfmt on OHOS; keeps gettext out of the link line |
| `--disable-shared` `--enable-static` | default package shape; libnsl is not a system lib on OHOS |
| `--disable-dependency-tracking` | avoids `.deps` bookkeeping temp dirs on HMDFS |

## Upstream tests
None. `Makefile.am` is `SUBDIRS = po src`, there is no `TESTS` /
`check_PROGRAMS` anywhere and the release tarball contains no test directory.
Verified with `grep -rn "TESTS\|check_PROGRAMS" Makefile.am src/Makefile.am`
(no output) and `find . -type d -iname '*test*'` (no output).

## Products
- `lib/libnsl.a` (static, default) / `libnsl.so.3` when `-o shared=True`
- `include/rpcsvc/{ypclnt.h,yp_prot.h,yp.h,ypupd.h,yppasswd.h,yp.x,yppasswd.x}`
- `lib/pkgconfig/libnsl.pc`

## Runtime notes
- `/tmp` on HarmonyOS PC is a read-only EROFS; use `TMPDIR=$HOME/tmp`.
- `getdomainname()` is present in the OHOS musl libc (returns `Unknown` when
  unset), so the `HAVE_TIRPC`-independent `yp_get_default_domain()` path works.

## HarmonyOS PC portability fixes (required)

### 1. `CONFIG_SHELL` must be `/bin/sh`

`configure` is autoconf 2.69. Autoconf probes the shell that started it; if
that shell lacks the bash-isms it needs it scans `/bin`, `/usr/bin`, `$PATH`
for the first of `sh bash ksh sh5` and **re-executes itself with it**. On
HarmonyOS PC `/bin/sh` fails that probe, so autoconf re-execs through `bash`,
and bash cannot resolve a non-root working directory (`pwd`/`getcwd()` fail
with EACCES/ENOTSUP on the hmfs/hmdfs mount). The re-executed configure dies
in its first probe:

```
configure: error: working directory cannot be determined
```

`/bin/sh` has no such defect and autoconf honours a **pre-set** `CONFIG_SHELL`
(skipping the search and the re-exec). The profile `[buildenv]` exports
`CONFIG_SHELL=/data/service/hnp/bin/bash` and `ConanFile.run()` always wraps
the command with that aggregated `conanbuild` env, so the recipe uses an
inline command-prefix assignment, which is the only injection point that wins.
See knowledge drafts DRAFT-E551 and DRAFT-6487.

### 2. Explicit native GNU triplet

The bundled `config.guess` (Autoconf 2.69, 2015) does not know
`uname -s` = `HarmonyOS`:

```
configure: error: cannot guess build type; you must specify one
```

Passing `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
(identical, i.e. a native build) skips `config.guess`/`config.sub` entirely.
The compiler still comes from the profile's `tools.build:compiler_executables`
(OHOS clang) and the OS branch is Linux. Same approach as the merged
`classads/1.0.10` and `cityhash/1.1.1` recipes. The alternative route
(re-anchoring a `config.guess`/`config.sub` portability patch for the old
script generation) is described in knowledge draft DRAFT-E564.

### 3. In-source build, no conan-provided cwd

The command `cd`s into the source tree instead of passing `cwd=`: on HMDFS a
conan-provided cwd triggers a `getcwd` storm in the child shell, while an
internal `cd` tracks `PWD` and avoids it (DRAFT-6487).

### 4. `--disable-nls`

No installed message catalogues and no `msgfmt` on OHOS. With `ENABLE_NLS`
undefined `libintl.h` maps `gettext()` to the identity macro, so no gettext
dependency is needed.
