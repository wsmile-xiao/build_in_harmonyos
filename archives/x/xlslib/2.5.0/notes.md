# xlslib 2.5.0 adaptation notes

## Overview

- Upstream: `xlslib-package-2.5.0.zip` (SourceForge, sha256
  `05a5d052ffdd6590755949d80d16a56285561557bc9a5e887e3b8b3fef92a3f3`).
  The archive unpacks to `xlslib/xlslib/` which contains the Autotools project
  (`configure.ac` + shipped `configure`/`Makefile.in`); the top-level
  `xlslib/OpenEXR/` directory only holds unrelated Windows VC project files and
  is not part of the build.
- Build system: Autotools (bundled automake 1.13-era generated files, libtool
  2.2.10). C++ library producing `libxls.a` (`xlslib_core` namespace), headers
  installed under `include/xlslib/`.
- License: BSD-2-Clause.

## Adaptation decisions

1. **`shared` option declared**. `package_type = "library"` requires a
   `shared` option in Conan 2, otherwise `conan create` fails with
   `Package type is 'library', but no 'shared' option declared`. Default is
   `shared: False`, matching the other `library` recipes in this repo.

2. **Static-only build (`--disable-shared`)**. The bundled libtool 2.2.10
   emits `#!/bin/bash` wrapper scripts for the `check` programs when shared
   libraries are produced. OHOS has no `/bin/bash`, so shared mode would make
   `make check` (and the packaged tests) fail with `Bad substitution`. Static
   linking also keeps the .so out of the OHOS system lib path. See
   `knowledge/drafts/DRAFT-libharu-2.3.0-missing-dt-soname*` and the general
   libtool-wrapper class of failures.

3. **`0001-config-sub-aarch64.patch`**: the bundled 2009 `config.sub` has no
   aarch64 case, so `configure` rejects the canonical host. The patch accepts
   `aarch64-*-linux*` / `aarch64-*-ohos*`. On OHOS the recipe passes
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
   (native, build == host) so the old `config.guess` is never consulted.
   Same approach as `archives/a/a52dec/0.7.4`.

   All three patch files are written with a `pristine/` / `modified/` leading
   path component, so every `conandata.yml` patch entry must set `strip: 1`.
   Conan's `patch()` defaults to `strip=0`; without `strip: 1` it looks for
   the file at the literal `pristine/config/config.sub` path and fails with
   `ConanException: Failed to apply patch`. Verified locally that all three
   patches apply cleanly with `patch -p1` on the flattened source tree.

4. **`0002-test-makefile-in-link-fix.patch`** (and `0003` for the `.am`
   consistency copy): the upstream check programs linked with
   `-static -lstdc++`, and `testC` (a C driver) was linked with the C compiler
   with `-lstdc++` *before* `libxls.a`. On modern toolchains and on OHOS this
   fails: `-static` needs a static libc (unavailable on OHOS), `-lstdc++` does
   not exist on OHOS (libc++ is the C++ runtime), and the link order breaks the
   C driver even on glibc. Fix: drop `-static -lstdc++` from all four check
   programs and drive `testC` through the C++ linker (`--tag=CXX $(CXXLD)`), so
   the C++ runtime is linked automatically and correctly on every platform.

5. **No autotools regeneration**: the shipped generated files are older than
   their `.ac`/`.am` sources, so a plain `make` invokes `autoconf`/`automake`
   (not installed on the worker). The recipe touches the generated
   `configure`/`Makefile.in`/`aclocal.m4`/`xlconfig.h.in` files after
   `apply_conandata_patches` (with `configure` touched last) so the `am--refresh`
   rules become no-ops.

## Upstream tests

- `make check` runs `testCPP` (10 sub-tests), `testC` (1), `PR2859188` (3) and
  `PR3076678` (1) — 15 MD5-based assertions in total behind 4 automake test
  entries. Each test dumps generated .xls files into `targets/test/` and
  compares MD5 against the shipped `*.md5` files (non-empty reference hashes,
  so this is not an empty-file comparison). Local x86_64 validation shows
  `All 4 tests passed` with `PASS: testCPP/PASS: testC/PASS: PR2859188/
  PASS: PR3076678` and `make check` exit 0; the HarmonyOS aarch64真机 run is
  performed by the hmbs preflight and its logged counts feed the PR body.

## Test package

- `test_package/test_xlslib.cpp` calls the real library API: `workbook` +
  `worksheet` creation, `label`/`number`/`blank` cells, `wb.Dump("test.xls")`,
  then verifies the file exists and is non-empty (4 assertions). Verified
  locally: compile + run OK, produces a 13 KB `test.xls`.
- Local (x86_64, gcc 13) full-flow validation: configure + `make -j4` +
  `make check` all pass after applying the three patches with the touch
  workaround.

## PR body notes

- 适配路径：路径 A（基础适配）。
- The hard-gate markers `HMBS_UPSTREAM_TEST_RESULT` and
  `HMBS_TEST_PACKAGE_RESULT` are emitted by `conanfile.py` / the test package
  conanfile with counts parsed from real test output.

## Round: configure exec refused on OHOS hmdfs (fixing_verification)

Root cause (new, distinct from the previous `strip: 1` patch fix which is now
confirmed working because the build advanced past apply_conandata_patches):

- The release tarball is a `.zip`, so extraction does NOT set the execute bit on
  `configure` (mode 0644), and the OHOS hmdfs user partition
  (/storage/Users/currentUser) refuses direct #!-script exec regardless of file
  mode (EACCES -> shell rc=126 "Permission denied"). This is the exact mechanism
  documented in knowledge/drafts/DRAFT-cdb-20251021-hmdfs-shebang-script-exec-refusal.md
  (distinguish: rc=126 "Permission denied" = exec refused, not a missing/bad
  shebang interpreter).

- HMBS platform capabilities report `chmod:0` on this device, so a
  `os.chmod(configure, 0o755)` fix would not help anyway.

Fix: run the bundled configure through the sh interpreter instead of exec'ing it
directly. conanfile.py no longer calls autotools.configure(); it calls the new
_configure_via_sh() which reads the same configure_args from conanbuild.conf (via
conan.tools.build.load_toolchain_args) and runs
`sh "<source>/configure" <args>`. Shebang exec is not involved, so neither an
exec bit nor hmdfs exec permission is required.

- make / install / make check are unaffected: make is a real binary, libtool and
  config.status are invoked via $(SHELL) in autotools-generated Makefiles, and the
  four check programs (testCPP/testC/PR2859188/PR3076678) are compiled ELF
  binaries (ELF exec is unrestricted on hmdfs per the DRAFT).

- The readonly_tmp diagnostic came from the preflight wrapper itself
  (preflight.sh creating /tmp/shnsv1du.tmp), not from this recipe; the recipe does
  not write to /tmp, so no tmpdir change is needed.

## Round (focus: readonly /tmp + getcwd working-directory error)

New failure (compile stage):
- `preflight.sh[306]: can't create temporary file /tmp/shluygnt.tmp: Read-only
  file system` (the preflight sandbox mounts /tmp read-only / erofs).
- `shell-init/job-working-directory ... getcwd: cannot access parent
  directories` and `configure: error: working directory cannot be determined`
  when `sh configure` runs. HMDFS cannot resolve the working directory via
  getcwd; a POSIX shell falls back to the exported $PWD (logical path) for its
  `pwd` builtin, and the autoconf script aborts when it cannot determine cwd.

Earlier note ("no tmpdir change is needed") is superseded: although the /tmp
line came from the preflight wrapper, the recipe now hardens its own configure
environment so it is independent of a read-only /tmp and of getcwd.

Fix (mirrors libfreexl / aldo / libe131 OHOS-autotools precedents, adapted):
- `_resolve_shell()` -> always /bin/sh (hmbs-injected, HMDFS-safe; avoids the
  CI profile CONFIG_SHELL pointing at a missing HNP bash that breaks autoconf
  re-exec).
- `_writable_tmp(fallback)` -> pick a build-local writable temp root first,
  then the injected HMBS_TMPDIR/TMPDIR/TMP/TEMP chain, then
  HMBS_AUTOCONF_MKTEMP_FALLBACK (path form); never /tmp.
- `generate()`: forward TMPDIR/TMP/TEMP + SHELL/CONFIG_SHELL + PWD (-> build
  folder) + HMBS_* capability flags via `tc.generate(env=...)` and via
  buildenv_info so they land in conanbuild.sh with correct ordering vs the
  profile [buildenv].
- `build()`: sync os.environ with the same shell/tmp/PWD before configure so
  every child (configure re-exec, conftest, make check) inherits them even if
  conanbuild.sh is not sourced.  Harden the shipped configure script itself:
  relax `umask 077` -> `umask 022` and change `ac_pwd=\`pwd\`` to
  `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"` so the "working directory
  cannot be determined" check uses the exported $PWD when HMDFS getcwd fails
  (aldo precedent).

No test is skipped; `make check` (4 automake entries / 15 MD5 assertions) and
the test_package assertions are unchanged.


## Round (focus: upstream testC iconv assertion, fixing_verification)

New failure (upstream_test stage): `make check` runs the four automake tests,
three pass (testCPP / PR2859188 / PR3076678) but `testC` aborts with

    Assertion failed: !(cd == (iconv_t)(-1)) at line 761 (wide2str16) in xlslib/globalrec.cpp

`wide2str16` (src/xlslib/globalrec.cpp) calls
`iconv_open(UCS_2_INTERNAL, iconv_code)`. On OHOS the bundled `common.h`
takes the non-glibc branch `#define UCS_2_INTERNAL "UCS-2-INTERNAL"`.
OHOS uses musl libc whose iconv recognise only `"ucs2"/"ucs2be"/"ucs2le"`
(and NOT the glibc-specific `"UCS-2-INTERNAL"`), so `iconv_open` returns
(iconv_t)-1 and the assert fires. The default `iconv_code` is "wchar_t"
(workbook.cpp constructor), which musl does recognise (fuzzy match on the
`wchart` alias), but the *target* "UCS-2-INTERNAL" is the unrecognised side.

Fix: new `0004-ucs2-internal-musl.patch` (registered in conandata.yml, strip:1)
makes `UCS_2_INTERNAL` expand to `"UCS-2LE"` on musl/Linux (`__linux__` /
`__OHOS__`), the native little-endian 16-bit layout that matches glibc's
`UCS-2-INTERNAL` on aarch64, while keeping `"UCS-2-INTERNAL"` for the other
non-glibc, non-Linux consumers (macOS/BSD with GNU libiconv).

No assertion/​test is removed; the four automake tests (15 MD5 assertions) run
unchanged. testC's explicit `xlsWorkbookIconvInType(w, "UCS-4-INTERNAL")` still
fails to switch the codec on musl (also a glibc-only name), but that is benign:
the codec stays "wchar_t", and on aarch64 wchar_t is exactly 32-bit UCS-4, so
the unicode labels in testC remain correct and the MD5 comparison still holds.

## Round (focus: upstream testC iconv assertion, verification + robustify 0004)

The 0004 patch (UCS_2_INTERNAL -> musl-recognised codec) was NOT present in the
last real preflight: its log exports only 3 patch files (0001/0002/0003) and
0004 was authored after that run; the immediately preceding "failures" were
model-provider stream/HTTP errors, not preflight verdicts. So 0004 is a sound,
never-verified fix. This round confirmed the root cause from the actual musl
source and strengthened the patch.

Verification of root cause against musl iconv (src/locale/iconv.c):
- iconv_open uses `find_charmap` with `fuzzycmp`, which *skips non-alphanumeric
  characters* in the requested name. So the alias "wchart" (codec WCHAR_T) also
  matches "wchar_t" (underscore skipped) -> the `iconv_code` SOURCE ("wchar_t"
  from the workbook constructor) IS recognised on musl.
- The TARGET "UCS-2-INTERNAL" folds to "ucs2internal", which matches NO codec
  alias (only ucs2/ucs2be/ucs2le exist) -> iconv_open returns (iconv_t)-1 and
  the XL_ASSERT in wide2str16() (globalrec.cpp:761) throws, aborting testC.
  This is exactly the `Assertion failed: !(cd == (iconv_t)(-1))` seen in the log.
- testC hits this path because `writeUnicodeLabel` writes non-ASCII WIDE labels
  (hiragana / Latin-1 accented) via label_t(ustring) -> wide2str16(). testCPP
  only uses ASCII char labels (label_t(string)/char2str16), which do not reach
  wide2str16's iconv branch, so it passes even pre-patch --- this reconciles the
  "testCPP passes / testC fails while both default iconv_code to wchar_t".

Patched result (0004-ucs2-internal-musl.patch, strip:1):
- On `__linux__ || __OHOS__`, map UCS_2_INTERNAL to the native-endian 16-bit
  musl codec: "UCS-2LE" on little-endian, "UCS-2BE" on big-endian
  (`__BYTE_ORDER__ == __ORDER_BIG_ENDIAN__`), matching glibc's "UCS-2-INTERNAL"
  in-memory layout. Other non-glibc platforms keep "UCS-2-INTERNAL" (macOS/BSD
  with GNU libiconv).
- Conan patch applies cleanly (patch -p1 dry-run+apply OK). Byte-order branch
  added this round; on aarch64 (LE) it selects "UCS-2LE" as before, so behaviour
  is unchanged on the target but no longer silently wrong on hypothetical BE.

All 4 patches apply in order on the flattened tree and the conandata.yml 0004
entry/strip:1 are consistent. All library iconv_open call sites use
UCS_2_INTERNAL as target and "wchar_t"/"UTF-8" as source, both musl-recognised,
so the fix covers every path. No test or assertion is removed.


## Round (focus: package-install chmod/readonly failure, fixing_verification)

New failure (package stage): `autotools.install()` aborts inside libtool's
static-archive post-install:

    libtool: install: chmod 644 .../p//lib/libxls.a
    chmod: .../p//lib/libxls.a: No such file or directory
    make[2]: *** [Makefile:453: install-libLTLIBRARIES] Error 1

Root cause: the HMBS preflight sandbox strips the `chmod` capability
(HMBS_CAP_CHMOD=0) and installs a `runtime/.../bin/install` shim (_install_shim),
so GNU libtool 2.2.10's `--mode=install` for a static archive is unreliable:
its copy step (`$install_prog $file $oldlib`) then `old_postinstall_cmds`
(`chmod 644 $oldlib`) both depend on binaries/caps the sandbox cannot satisfy.
This is the classic clthreads OHOS package-stage obstacle (DRAFT-8958): on this
worker "调 make install 打包" fails regardless of code correctness.

Fix (adapts DRAFT-8958 clthreads paradigm): drop `autotools.install()` and stage
the package manually in `package()` -> `_manual_install()` using only
`shutil.copyfile` (no chmod, no `install` binary):
- `lib/libxls.a`  <- `src/.libs/libxls.a` (built archive, objdir=.libs).
- `include/xlslib/xlslib.h` <- `src/xlslib.h`.
- 49 `nobase_pkginclude_HEADERS` staged under `include/xlslib/` preserving the
  common/oledoc/xlslib subdir layout; `common/xlconfig.h` is configure-generated
  in the in-source build tree (folders.build=".") so it is copied from there.

The layout is identical to upstream `make install` (verified against
src/Makefile.am pkginclude/nobase_pkginclude lists and the installed consumer
`#include <xlslib.h>` + `cpp_info.includedirs=["include/xlslib"]`). build()
(configure-via-sh, make -j1, make check) is untouched; no test is skipped.
