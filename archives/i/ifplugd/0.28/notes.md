# ifplugd 0.28 adaptation notes

## Overview
- Build system: autotools (tarball ships pre-generated `configure` + `Makefile.in`, no autoreconf)
- Date: 2026-10-03
- Toolchain: clang/clang++ (OHOS aarch64, musl)
- Delivery: application (two daemons: `ifplugd` + `ifplugstatus`; upstream `sbin_PROGRAMS`, Conan maps sbindir to `bin/`)
- Status: built (pending HMBS preflight evidence)

## Upstream test audit
Upstream 0.28 provides no automated tests whatsoever:
- 65 files in `ifplugd-0.28.tar.gz`, no `tests/` or `test/` directory anywhere
- All `Makefile.am` (top/src/conf/doc/man/patches) define no `TESTS`, `check_PROGRAMS` or `check` target
- `make check` is only the automake-generated no-op (0 cases)
- Daemon runtime needs root + real Ethernet interfaces + kernel link ioctls; not executable as a CI assertion
Hence upstream static total 0 / executed 0 (`status: no_tests`), and the functional surface is covered by a real consumer test driving the packaged binaries (see below). Evidence: `probe2.py` file listing (65 entries) and `Makefile.am` inspection recorded in this task round.

## Adaptation changes
| # | File | Problem | Fix |
|---|------|---------|-----|
| 1 | configure (args) | 2005-era config.sub cannot canonicalise aarch64-OHOS host | Explicit `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos` (ifmetric precedent) |
| 2 | configure (args) | Hard-abort without lynx (`AC_MSG_ERROR`); xmltoman/subversion gate doc rebuild | `--disable-lynx --disable-xmltoman --disable-subversion` (binaries unaffected) |
| 3 | configure (args) | `--with-initdir` mandatory; default probes `/etc/init.d` missing on OHOS | `--with-initdir=${prefix}/etc/init.d` (staged under package) |
| 4 | configure (cache) | AC_FUNC_MALLOC cross false positive -> undefined `rpl_malloc` at link | Seed `ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes` (isatapd precedent) |
| 5 | configure (runtime) | `(umask 077 && mktemp -d)` scratch dir unwritable on HMDFS setgid | `replace_in_file` `umask 077` -> `umask 022`, keeping real mktemp (ifmetric/iec16022 precedent, no patch file) |
| 6 | build | Recursive `make -j2` jobserver needs mkfifo (denied on HMDFS) | `make -j1` |
| 7 | source perms | HMDFS checkout mode 660 strips +x from helpers | `chmod +x` on configure/config.guess/config.sub/install-sh/missing/mkinstalldirs (E490), tolerant `try/except OSError` when HMBS reports `HMBS_CAP_CHMOD=0` |
| 8 | generate (env) | 2026-10 preflight: dependency `libdaemon/0.14` configure died with `C compiler cannot create executables` (E002: `/tmp` erofs, clang tempfiles need writable TMPDIR) and `/data/service/hnp/bin/bash: inaccessible` (stale profile SHELL) | Build-local TMPDIR via `Environment(scope=build)`: reuse HMBS-injected `TMPDIR` after real `makedirs+open+unlink` probe (no `os.access`, E046), else `build_folder/tmp`; `SHELL`/`CONFIG_SHELL` set to verified on-device shell (`$SHELL` > `/bin/sh` > `/system/bin/sh` > PATH `sh`/`bash`) (precedent: iec16022 0.3.1, ical2html, coinor-vol draft) |
| 9 | build (exec) | Same preflight: shebang-exec of `configure` refused on native OHOS host before Autoconf starts (E232; `CONFIG_SHELL` alone cannot help) | On `settings_build.os == OHOS`, run `"<shell>" "<source>/configure" <autotools._configure_args>` inside `Environment.apply()` (keeping toolchain args authoritative), `autotools.configure()` elsewhere (precedent: iec16022 0.3.1 `E232`) |

Dependency `libdaemon/0.14` is provided via `PkgConfigDeps` + `VirtualBuildEnv` for upstream `PKG_CHECK_MODULES(LIBDAEMON, libdaemon >= 0.5)`.

## Consumer test (test_package)
`test_package/smoke.sh` (L0c source) drives the packaged binaries with no privilege or interface needed; 6 deterministic scenarios, PASS incremented exactly once per scenario (sub-checks inside a scenario only fail it, never add extra increments; no stdout string-counting or arithmetic fix-ups):
1. Both binaries exist under package `bin/` (or `sbin/`) and are executable — proves install layout
2. `ifplugd -h` prints the full usage banner (`Network Interface Plug Detection Daemon` + `Usage:` + `--iface`) — proves link + getopt wiring is real, not a stub
3. `ifplugd -v` prints `ifplugd 0.28` — proves version path
4. `ifplugd --definitely-not-an-option` exits non-zero with `unrecognized option` — proves argument validation runs
5. `ifplugstatus -h` prints its usage (`[options] [INTERFACE]` + `--help`) — proves second binary links
6. `ifplugstatus --definitely-not-an-option` exits non-zero with `unrecognized option` — proves second binary validation runs
Any failed assertion exits non-zero, so `conanfile.py test()` `self.run()` fails instead of silently passing.
Machine-evidence markers (HMBS hard gate) are printed by `smoke.sh` itself on the device, exactly once each, in both pass and fail paths (fail path reports `passed:false` with the scenarios passed so far, then exits 1):
- `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"sh smoke.sh","discovered":6,"passedCount":6}` (counts from the in-script PASS/TOTAL counter; self-check `passed + failed == executed`, `executed <= discovered`)
- `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"upstream 0.28 ships no tests dir and no TESTS/check_PROGRAMS in any Makefile.am (audit: test_package/MANIFEST.yml)"}`

## Test numbers (four-way consistent: manifest.yaml / notes.md / MANIFEST.yml / PR body)
- Upstream static total: 0
- Upstream executed: 0 (`no_tests`)
- New consumer tests: 1 script (`smoke.sh`), 6 scenarios / 6 assertions (1:1; MANIFEST `test_scenario_count: 6`, `assertion_count: 6`)
- Machine markers: `HMBS_TEST_PACKAGE_RESULT` (`discovered: 6`, `passedCount: 6` on pass) and `HMBS_UPSTREAM_TEST_RESULT` (`status: no_tests`, all counts 0 + reason), printed by `smoke.sh` on-device in both pass and fail paths

## Dependency / preflight finding (2026-10-04 round)
- Preflight `conan create` fails while building the **dependency** `libdaemon/0.14` (not `ifplugd` itself): its `configure` reports `/data/service/hnp/bin/bash: inaccessible or not found` (stale profile `[buildenv]` SHELL/CONFIG_SHELL in `ci/conan/profiles/ohos-aarch64`) followed by `configure: error: C compiler cannot create executables` at `AC_PROG_CC`.
- The published `libdaemon/0.14` recipe (HEAD `archives/l/libdaemon/0.14/conanfile.py`) has no E002 (writable TMPDIR) / E232 (verified-shell configure launch) hardening, so a from-source rebuild cannot survive the drifted worker env. Sibling evidence: `popt/1.16` (dep of `iec16022`) is equally unhardened yet resolves, because its registry binary is reused and never rebuilt.
- No change inside the `ifplugd` package tree can propagate SHELL/TMPDIR into the dependency's own `generate()`/`build()` (Conan build env is per-package; deps build before the consumer), and single-PR atomicity forbids touching `archives/l/libdaemon` here. Vendoring libdaemon sources was rejected (duplicates a registry package / hides the dependency graph).
- Recommended routing for HMBS backend: refresh the profile shell to the HMBS-injected `/bin/sh`, ensure a `libdaemon/0.14` binary matching the current profile exists in the `ohpcd` remote, or schedule a `libdaemon` re-adaptation PR carrying the E002/E232 hardening; then re-run this package's preflight unchanged.

## Risks
- Link-detection runtime paths (MII/ethtool/netlink ioctls on real NICs) cannot be exercised in the container/CI userland; option-parser surface is asserted instead, honestly reported (not presented as hardware coverage).

## Dependency / preflight finding (2026-10-08 round)
- Re-observed identical failure in HMBS preflight: `conan create` fails while building the **dependency** `libdaemon/0.14` (package build folder `.../p/b/libda2c04ae93d5d21/b/build-release`), not `ifplugd` itself. Same two signatures as 2026-10-04: `.../src/configure: /data/service/hnp/bin/bash: inaccessible or not found` (stale profile [buildenv] SHELL/CONFIG_SHELL) then `configure: error: C compiler cannot create executables` at AC_PROG_CC (`autotools.configure()`, libdaemon recipe line 85).
- ifplugd recipe itself already carries E002 (writable TMPDIR with real makedirs+open+unlink probe) and E232 (verified-shell configure launch on settings_build.os == OHOS) hardening; no new signal points at ifplugd sources, options, or test_package. Upstream test audit unchanged (0 tests, no_tests).
- No compliant in-PR code change exists: Conan build env is per-package (deps build before consumer generate()/build()), so SHELL/TMPDIR hardening inside `archives/i/ifplugd/0.28` cannot propagate into libdaemon build; single-PR atomicity (W2/JC6) forbids touching `archives/l/libdaemon` or `ci/conan/profiles/ohos-aarch64` here; vendoring stays rejected per 2026-10-04 rationale.
- Routing unchanged: backend to refresh profile shell to HMBS-injected /bin/sh, ensure a libdaemon/0.14 binary matching the current profile/recipe revision exists in ohpcd remote (libdaemon manifest status published 2026-04-26 predates current recipe revision), or schedule a libdaemon re-adaptation PR with E002/E232 hardening; then re-run ifplugd preflight unchanged. This round makes no functional conanfile/test change to avoid faking a pass.

## Strategy change (2nd identical fingerprint: bundle libdaemon privately)
- 2026-10-04 and 2026-10-08 preflights fail identically inside the
  **dependency** `libdaemon/0.14` rebuild (stale profile SHELL
  `/data/service/hnp/bin/bash` inaccessible + `C compiler cannot create
  executables` at AC_PROG_CC, libdaemon recipe `autotools.configure()`
  line 85). Previous round documented this as backend routing with no
  functional change; the failure repeated verbatim, so a different
  in-PR strategy is required.
- New approach: remove the external `requires("libdaemon/0.14")` edge and
  build an IDENTICAL upstream libdaemon 0.14 tarball (same URL + sha256 as
  `archives/l/libdaemon/0.14/conandata.yml`, declared under
  `conandata.yml:vendor_libdaemon`) as a private STATIC prefix
  (`build_folder/private-prefix`, `--enable-static --disable-shared`)
  used only to satisfy ifplugd's `PKG_CHECK_MODULES(LIBDAEMON)` probe via
  build-scope `PKG_CONFIG_PATH`. Nothing extra is packaged or exported;
  final artifacts remain the two ifplugd binaries (statically linked
  against the private lib, no runtime .so dependency).
- The private build reuses this recipe's proven hardening (verified shell
  launch, real-probe writable TMPDIR, `umask 077`->`022`) plus libdaemon's
  own published fixes replicated without patch files: `config.sub`
  `linux-ohos`/`-ohos` recognition (patches 0001/0002 equivalent),
  `examples/testd.c` `sys/unistd.h`->`unistd.h` (patch 0004 equivalent).
  Explicit `--build/--host` triplets match the ifplugd precedent, so no
  `config.guess` change is needed.
- Job control now follows the injected `tools.build:jobs` conf (HMBS=1)
  with single-job fallback, and both `make` calls use the plain helper /
  conf-derived flags (no duplicated `-j1` passthrough). `make` executable
  prefers `HMBS_MAKE` when injected.
- Honesty safeguards: no assertions removed, no tests skipped, upstream
  audit unchanged (`no_tests`, total 0); consumer `smoke.sh` (6 scenarios)
  and both machine-evidence markers untouched. TODO: restore
  `self.requires("libdaemon/0.14")` once libdaemon is re-adapted with
  E002/E232 hardening and its registry binary matches the current profile.

## Fix iteration (3rd identical fingerprint: inherit toolchain args + self-diagnosis)
- The 2nd strategy (private libdaemon build) moved the failure forward:
  the stale-SHELL signature is gone (verified-shell launch works), but the
  vendored configure now fails at `checking for
  aarch64-unknown-linux-ohos-gcc... /data/service/hnp/bin/clang` with `C
  compiler cannot create executables` in `.../b/vendor-libdaemon`
  (ifplugd recipe `build()` -> `_build_private_libdaemon`, Error 77).
- Root cause of the NEW failure: the hand-written bare configure line
  (`--prefix/--build/--host/--enable-static/--disable-shared` only)
  drops the AutotoolsToolchain context, so the compiler probe runs
  without the toolchain flags and fails on a healthy toolchain. Fix:
  `_vendored_configure_args()` inherits `autotools._configure_args`
  (shlex token filter: drop only ifplugd-specific `--disable-lynx/
  --disable-xmltoman/--disable-subversion`, `--with-initdir=`, and the
  two `ac_cv_func_*` cache vars; redirect `--prefix` to the private
  prefix; append static switches) and configures out-of-source in
  `build_folder/private-build`.
- `_dump_config_log()` added: any configure failure now prints the
  effective `CC/CFLAGS/LDFLAGS/SHELL/CONFIG_SHELL/TMPDIR` plus the last
  60 lines of `config.log` (bounded, preflight stdout only) so the next
  round sees the real compiler error instead of guessing. Applied to both
  the private-libdaemon and the main ifplugd configure steps.

## Fix iteration (4th round: inherit conanbuild env, not just args)
- 3rd strategy inherited toolchain ARGS via _vendored_configure_args but still failed identically: checking for aarch64-unknown-linux-ohos-gcc... /data/service/hnp/bin/clang then C compiler cannot create executables, with _dump_config_log printing private-libdaemon env: CC=None CFLAGS=None LDFLAGS=None. That line is the proof: manual self.run() without env=conanbuild runs outside the VirtualBuildEnv+AutotoolsToolchain aggregate env, so CC/sysroot/flags are absent even though args look right. Previous hypothesis (bare configure line drops flags) was half-right; the missing piece is ENV, not ARGS.
- Different route this round: keep args inheritance, but run all manual configure/make/install steps with env=conanbuild so CC/CFLAGS/LDFLAGS/sysroot from the generated toolchain reach the probe, stacking with the SHELL/TMPDIR Environment.apply() overlay (generate() already saved SHELL/TMPDIR into conanbuild_hmbs_shell_tmpdir, so values agree). Applied to private-libdaemon configure+make+install and to the main ifplugd verified-shell configure on settings_build.os==OHOS. Autotools helper paths (autotools.configure()/make()) already manage env internally and are untouched.
- No test/dependency-graph change: still private static libdaemon (same URL+sha256), no requires() restore, no assertion removal, upstream audit unchanged (no_tests, total 0), smoke.sh markers untouched. Validation left to HMBS preflight rerun.

## Fix iteration (5th round: explicit CC/CXX from profile conf)
- 4th strategy (env=conanbuild passthrough) failed with the IDENTICAL fingerprint: private-libdaemon env still CC=None CFLAGS=None LDFLAGS=None, same clang probe then Error 77 at the same line (now line 341 with env arg). Comparison result: conanbuild aggregate does not carry the Autotools toolchain CC export on this worker; toolchain exports only reach the helper's own configure(), never a manual self.run() for a second source tree. Repeating env-only passthrough would be the prohibited same-strategy retry.
- Different route this round (precedent: merged archives/i/ical2html/3.0 conanfile.py _compiler_paths/build): explicitly resolve CC/CXX from tools.build:compiler_executables conf (profile: /data/service/hnp/bin/clang/clang++) with which()/hardcoded fallbacks, log them, and define CC/CXX in the Environment overlay for BOTH manual configures (private libdaemon + main ifplugd OHOS branch). env=conanbuild is kept so SHELL/TMPDIR/buildenv still stack. No shlex/args change (probe reached compiler check, so arg quoting is not the blocker), no dependency/test change.

## Fix iteration (6th round: pin OHOS toolchain clang over host which())
- 5th strategy (explicit CC from conf + which fallback) moved the failure forward: private-libdaemon env now shows CC=/storage/Users/currentUser/.harmonybrew/bin/clang (no longer None), yet configure still dies at the same probe with checking for aarch64-unknown-linux-ohos-gcc... /data/service/hnp/bin/clang then Error 77. Comparison: CC is exported but it is a HOST .harmonybrew clang that cannot create OHOS executables; shutil.which("clang") shadowed the profile OHOS toolchain. Repeating explicit-CC with the same order would be the prohibited same-strategy retry.
- Different route this round: keep explicit CC/CXX injection, but change SELECTION ORDER to conf-on-disk first, then the known OHOS path /data/service/hnp/bin/clang(++), and demote PATH which() to last resort; also log the raw conf c/cpp values. The probe line itself confirms the right compiler lives at /data/service/hnp/bin/clang. No args/test/dependency change.

## Fix iteration (7th round: native minimal private configure, drop CC shadowing)
- Why rounds 4-6 all failed identically: the `os.environ` diagnostic (`CC=None`, then `CC=.harmonybrew`) never measured the real subprocess env. `self.run(..., env="conanbuild")` layers the toolchain exports ON TOP of `os.environ`, so the probe line always showed the toolchain clang (`/data/service/hnp/bin/clang`) while the diagnostic showed the overlay value. Rounds 5-6's CC-pinning therefore never reached the compiler -- the subprocess env was identical in rounds 4, 5 and 6, which is exactly why the fingerprint never changed. Continuing to reorder CC selection would be the prohibited same-strategy retry.
- Different route this round (evidence: published `archives/l/libdaemon/0.14/conanfile.py` in git HEAD, which never forced triplets and built with plain `autotools.configure()`; iec16022 0.3.1 documents forced triplets as harmful, E007):
  1. Private libdaemon configure drops the inherited cross triplets entirely (`_private_configure_args`: only `--prefix=<private> --enable-static --disable-shared`). The `--host=aarch64-unknown-linux-ohos` inheritance (round 3) turned the probe into a cross link this 2004-era configure cannot complete here; the device clang already targets OHOS natively, so a native probe compiles, links AND runs conftest. Main ifplugd build keeps its forced triplets (ifmetric precedent for that codebase).
  2. All bare `CC`/`CXX` overlays removed (private + main); `_compiler_paths` deleted. The toolchain env from `env="conanbuild"` is used exactly as the proven plain-helper path provides it; a bare-CC override would additionally strip toolchain `CFLAGS`/`LDFLAGS`.
  3. `priv_build`/`prefix` created under `os.umask(0o022)` (HMDFS setgid safety, previously untouched).
  4. Added a same-env hello-world pre-probe (`$CC -o hmbs_cc_probe hmbs_cc_probe.c && ./hmbs_cc_probe` with `env="conanbuild"`): failure before configure proves the toolchain env itself is broken; success isolates the fault to the old configure script. Single-round disambiguation.
  5. `_dump_config_log` now returns the tail and every configure failure raises `ConanException` with `CONFIG_LOG_TAIL` embedded in the message body, so the real compiler error can no longer be summarised away from focused digests.
## Fix iteration (8th round: toolchain drift fallback, idsgrep precedent)
- This round's pre-probe fails BEFORE any configure logic: `CC=/data/service/hnp/bin/clang` then `/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found` (Error 127). The profile pins `tools.build:compiler_executables` to that path, but the file is gone/broken on this runner. Previous rounds proved an `Environment` overlay alone never wins (`self.run(env="conanbuild")` layers toolchain exports on top of `os.environ`), so rounds 5-6's CC-pinning never reached the subprocess.
- Different route this round (precedent: merged `archives/i/idsgrep/0.6/conanfile.py` `_resolve_compiler`/`_fix_compiler`, same fingerprint): `_resolve_compiler()` probes the conf path with existence + `--version`; healthy machines keep it (zero change); broken ones fall back to PATH `clang/clang-15/cc/gcc` (+ `clang++` sibings) with the same probe. `_fix_compiler()` applies the triple-scope override: `os.environ` CC/CXX + rewrite of generated `conanbuild/toolchain/*.sh` refs + inline `CC=... CXX=...` assignments on every manual `self.run` (pre-probe, both configures, both makes). Nearest scope wins; `CFLAGS`/`LDFLAGS` untouched.
- Applied to private-libdaemon pre-probe/configure/make/install and to the main ifplugd OHOS verified-shell configure + make (replacing `autotools.make()` there so the fallback reaches make too). Non-OHOS local path unchanged. No test/dependency-graph change: still private static libdaemon (same URL+sha256), no `requires()` restore, no assertion removal, upstream audit unchanged (`no_tests`, total 0), `smoke.sh` markers untouched. If no PATH compiler passes `--version`, the recipe raises an explicit "no working C compiler ... Environment fault" for infra routing instead of a misleading Error 77.
- Post-round syntax fix: the `_fix_compiler` insertion left `def _patch_text` with a 3-space indent (`IndentationError` at load, conanfile line 296); re-indented to 4 spaces. No logic change.

## Fix iteration (9th round: native ohos triplets for private libdaemon)
- This round's failure is NEW (not the compiler fingerprint): vendored
  libdaemon configure dies before any compiler probe with
  `vendor-libdaemon/config.guess: unable to guess system type`
  (`UNAME_SYSTEM=HarmonyOS`) then
  `configure: error: cannot guess build type; you must specify one`.
  Round 7 had dropped all explicit triplets (`_private_configure_args`
  = prefix + static switches only), so the 2008-era config.guess ran and
  cannot recognise HarmonyOS. The compiler-drift fallback (round 8,
  idsgrep precedent) already works this round (log shows
  `compiler fallback C=.../.harmonybrew/bin/clang` + rewritten toolchain
  refs); the blocker is purely the missing build-type specification.
- Fix: `_private_configure_args` now passes explicit NATIVE triplets
  `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
  (build==host, so cross_compiling=no and the old configure can
  compile+link+run conftest with the device clang that already targets
  OHOS natively; avoids both config.guess and the round-3 cross-link
  failure where build=gnu/host=ohos forced a prefixed
  `aarch64-unknown-linux-ohos-gcc` lookup). Added `_patch_config_sub`
  helper (tolerant, log-only on wording drift) covering both the vendored
  libdaemon and the main ifplugd `config.sub` (same autoconf 2.59 era,
  same linux-ohos/-ohos additions as libdaemon patches 0001/0002), so the
  explicit ohos triplets canonicalise instead of aborting. Main ifplugd
  keeps its gnu/ohos cross triplets (ifmetric precedent for that tree).
- No test/dependency change: still private static libdaemon (same
  URL+sha256), no requires() restore, no assertion removal, upstream
  audit unchanged (no_tests, total 0), smoke.sh markers untouched.
  Validation left to HMBS preflight rerun.

## Fix iteration (10th round: linux-gnu triplets for private libdaemon)
- Comparison with last round (different strategy required): the 9th round
  passed native ohos triplets (`--build/--host=aarch64-unknown-linux-ohos`)
  plus an exact-match `config.sub` patch. Preflight now fails INSIDE that
  patch path: `private libdaemon patch not needed (config.sub os list)`
  (anchor missed the real file wording) followed by
  `Invalid configuration 'aarch64-unknown-linux-ohos': machine
  'aarch64-unknown-linux' not recognized`. So exact-string patching of the
  2008 script is the fragile link -- repeating it with adjusted anchors
  would be the prohibited same-strategy retry.
- Different route this round: stop asking the 2008 script to understand
  ohos at all. Empirically verified with the vendored tarball's OWN
  `config.sub` (2008-01-23, fetched from the conandata URL):
  `aarch64-unknown-linux-gnu` canonicalises RC=0 while
  `aarch64-unknown-linux-ohos` fails RC=1 with byte-identical preflight
  error. `_private_configure_args` now uses
  `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
  (accepted verbatim, zero patching). Behaviour-neutral: libdaemon 0.14
  `configure.ac` has no host_os-dependent branches (only generic header /
  func probes), build==host keeps cross_compiling=no so all probes run
  natively, and OS defines come from the OHOS-targeting device clang, not
  the triplet string. The `_patch_config_sub` helper and both call sites
  are removed (main ifplugd tree ships no config.sub at all and its
  configure has no canonical macros, so its gnu/ohos toolchain args are
  accepted-but-unused there).
- No test/dependency change: still private static libdaemon (same
  URL+sha256), no requires() restore, no assertion removal, upstream
  audit unchanged (no_tests, total 0), smoke.sh markers untouched.
  Validation left to HMBS preflight rerun.

## Fix iteration (11th round: install-sh INSTALL rewrite for Error 64)
- Comparison with last round (different strategy required): the 10th round
  (linux-gnu triplets, zero config.sub patching) moved the failure forward:
  vendored libdaemon configure + make now succeed, and `make install`
  dies at `install-pkgincludeHEADERS` (7 headers via am__base_list) with
  `.../runtime/ifplugd-0.28/bin/install -c -m 644 ... Error 64` (EX_USAGE).
  Repeating triplet/configure tweaks would be the prohibited
  same-strategy retry -- the compiler path is proven working; the blocker
  is purely the device `install(1)` implementation.
- Root cause: the HMBS/toybox `install -c` probed into generated
  Makefiles (`INSTALL = .../bin/install -c`) cannot handle multi-source
  installs on HMDFS (single-file installs pass, batched header lists via
  am__base_list fail Error 64). Precedent: libnih 1.0.3 (1 header OK, 28
  headers Error 64, fixed by `/bin/sh install-sh -c`), lftp 4.9.3
  (install-man1 Error 64, _find_install_sh + INSTALL override), openfst
  E596-C (toybox install -c + chmod unsupported on HMDFS).
- Fix: `_find_install_sh()` locates the tarball's own `install-sh`
  (pure shell, needs no +x when driven as `<shell> install-sh -c`);
  `_patch_install_to_install_sh()` rewrites only the exact `INSTALL = ...`
  line in every generated Makefile to `<verified-shell> <install-sh> -c`
  (`INSTALL_DATA`/`INSTALL_PROGRAM` reference `${INSTALL}` and follow
  automatically; no make-command-line override per libnih prohibition).
  Applied after configure and before make/install in three scopes:
  private-libdaemon `priv_build` (vendor install-sh), main ifplugd
  `build_folder` in both OHOS and non-OHOS branches (source install-sh),
  plus a defensive idempotent re-apply at the start of `package()`.
  Content and modes unchanged; no test/dependency-graph change (same
  private static libdaemon URL+sha256, no requires() restore, no assertion
  removal, upstream audit unchanged no_tests total 0, smoke.sh markers
  untouched). Validation left to HMBS preflight rerun.

## Fix iteration (12th round: build-local pkg-config shim for PKG_CHECK_MODULES)
- Comparison with last round (different strategy required): the 11th round
  (install-sh INSTALL rewrite) moved the private libdaemon fully to
  `private libdaemon ready: .../private-prefix/lib/pkgconfig/libdaemon.pc`,
  but the MAIN ifplugd configure now dies in `PKG_CHECK_MODULES` with
  `configure: error: The pkg-config script could not be found or is too
  old`. The `.pc` file is ready and `PKG_CONFIG_PATH` already points at it
  (generate() scope=build); the missing piece is the `pkg-config` BINARY
  itself, which no preflight worker provides (`HMBS_BUILD_TOOLS` only
  probes cmake/make/ninja/python3). Repeating triplet/install tweaks would
  be the prohibited same-strategy retry -- the compiler and install paths
  are proven working; the blocker is purely the absent tool binary.
- Fix (hermetic, no new dependency edge): `_ensure_pkg_config_shim()`
  writes a minimal pure-shell `pkg-config` into
  `build_folder/pkgconfig-shim/`, answering ONLY the private libdaemon
  prefix (`-I<private>/include` / `-L<private>/lib -ldaemon`,
  `--exists`/`--modversion`/`--variable=`/`--atleast-pkgconfig-version`
  handled; unknown modules exit 1 so configure fails honestly instead of
  linking wrong flags). `configure.ac` has no other `PKG_CHECK`, so the
  narrow scope is complete. `generate()` exports `PKG_CONFIG="sh <shim>"`
  (the `sh` prefix makes exec chmod-proof under `HMBS_CAP_CHMOD=0`),
  `PKG_CONFIG_PATH`, preset `LIBDAEMON_CFLAGS`/`LIBDAEMON_LIBS`
  (belt-and-suspenders: pkg.m4 honors preset vars), and prepends the shim
  dir to `PATH`, all in build scope. `build()` re-ensures the file at the
  top (generate-cache safety) and mirrors the same exports in the OHOS
  verified-shell overlay. A `tool_requires("pkgconf/2.5.1")` edge was
  deliberately rejected: it would pull a Meson chain rebuild whenever its
  OHOS binary is absent from the remote.
- No test/dependency-graph change: still private static libdaemon (same
  URL+sha256), no requires() restore, no assertion removal, upstream
  audit unchanged (no_tests, total 0), smoke.sh markers untouched.
  Validation left to HMBS preflight rerun.

## Fix iteration (13th round: musl/OHOS source portability, main tree compile)
- Comparison with last round (different strategy required): the 12th round
  (pkg-config shim) moved the failure forward: private libdaemon now
  reaches `private libdaemon ready: .../libdaemon.pc` and the MAIN ifplugd
  configure succeeds, but `make` dies in `src/ifplugd.c` with 4 errors:
  `ethtool-local.h:25: unknown type name '__uint32_t'` (plus `__uint16_t`/
  `__uint8_t`) and `linux/socket.h:23: redefinition of 'sockaddr_storage'`
  via `nlapi.h` (`<sys/socket.h>` then `<linux/netlink.h>`). Repeating
  configure/install/pkg-config tweaks would be the prohibited
  same-strategy retry -- the blocker is purely source-level portability on
  the musl/OHOS sysroot, not toolchain env.
- Root causes (tarball-verified): `__uint32_t` et al. are glibc
  `<sys/types.h>` internals, absent on musl/OHOS; the kernel
  `<linux/socket.h>` copy of `sockaddr_storage` collides with the libc
  `<sys/socket.h>` one when `<linux/netlink.h>` pulls it in.
- Fix (new `_patch_ifplugd_portability()`, called in `build()` right after
  `apply_conandata_patches`, covering both source and build trees):
  `ethtool-local.h` gains `#include <stdint.h>` and uses standard
  `uint32_t/uint16_t/uint8_t`; every file including `<linux/netlink.h>`
  (`nlapi.h`, `ifmonitor.c`) pre-defines both `_LINUX_SOCKET_H` and
  `_UAPI_LINUX_SOCKET_H` before it so the kernel copy is skipped (netlink
  only needs `<linux/types.h>` plus its own `sockaddr_nl`). Unconditional
  and portable, no platform macro (no PF5 concern), tolerant to wording
  drift (anchor-checked, log-only on miss).
- No test/dependency-graph change: same private static libdaemon
  URL+sha256, no requires() restore, no assertion removal, upstream audit
  unchanged (no_tests, total 0), smoke.sh markers untouched. Validation
  left to HMBS preflight rerun.

## Fix iteration (14th round: keep linux/socket.h parsing, hide one struct)
- Comparison with last round (different strategy required): the 13th round
  (guard-skip of `<linux/socket.h>`) fixed the 4-error fingerprint
  (`__uint*_t` + `sockaddr_storage` redefinition) but produced a NEW
  2-error fingerprint in the same `src/ifplugd.c` TU:
  `linux/netlink.h:49: unknown type __kernel_sa_family_t` and
  `linux/rtnetlink.h:308: unknown type __kernel_sa_family_t` via
  `nlapi.h:30/31`. Proof from the log: the `__uint` errors are gone
  (ethtool half of round 13 works), and the new errors name the exact
  type that lives in the skipped file -- whole-file skipping is the wrong
  scope. Repeating guard defines would be the prohibited same-strategy
  retry.
- Different route this round: keep `<linux/socket.h>` parsing (so
  `__kernel_sa_family_t` stays visible) and hide ONLY the colliding
  struct via macro rename -- `#define sockaddr_storage
  __hmbs_hidden_sockaddr_storage` before `<linux/netlink.h>`, `#undef`
  right after the kernel netlink block (`nlapi.h`: after
  `<linux/rtnetlink.h>`; `ifmonitor.c`: after `<linux/if.h>`, which may
  re-pull the kernel socket header). Neither netlink header uses
  `sockaddr_storage` (tarball-verified: only `sockaddr_nl` /
  `__kernel_sa_family_t`), so the alias is behavior-neutral; the libc
  definition (already parsed from `<sys/socket.h>` above) is untouched.
  Unconditional, no platform macro (no PF5 concern). Applied to both
  `nlapi.h` and `ifmonitor.c` because the latter has its own direct
  `<linux/netlink.h>` include before `nlapi.h`.
- No test/dependency-graph change: ethtool `stdint.h` half unchanged,
  same private static libdaemon URL+sha256, no requires() restore, no
  assertion removal, upstream audit unchanged (no_tests, total 0),
  smoke.sh markers untouched. Validation left to HMBS preflight rerun.

## Fix iteration (15th round: TU-wide generic socket hide, interface.c)
- Comparison with last round (different strategy required): the 14th round
  (macro-rename hide anchored on the `linux/types.h`+`netlink` pair in
  `nlapi.h`/`ifmonitor.c`) works -- the log proves `src/ifplugd.c` now
  compiles, and the build moved to the NEXT TU `src/interface.c:30` with
  the SAME redefinition (`linux/if.h:23` -> `linux/socket.h:23` vs
  `sys/socket.h:377`, 1 error). The old per-file anchor never touched
  `interface.c` (it has no `linux/netlink.h`; its collider is
  `<linux/if.h>` after `<sys/socket.h>`). Repeating the same two-file
  anchor edit would be the prohibited same-strategy retry.
- Different route this round: replaced per-file anchors with a generic
  TU-wide rule -- every `.c`/`.h` containing BOTH `<sys/socket.h>` and at
  least one `<linux/*.h>` gets the hide opened before its FIRST
  `<linux/>` include at-or-after the socket line (fallback: first
  `<linux/>` overall) and closed after its LAST `<linux/>` include.
  Tarball-simulated coverage: `nlapi.h` (types->rtnetlink), `ifmonitor.c`
  (types->if.h), `interface.c` (if.h only, correctly leaving the
  pre-socket `sockios.h`/`if_ether.h` outside -- they pull no socket
  header), `wireless.h` (if.h, bonus: it is included by `interface.c`).
  `ifplugd.c` (no direct `sys/socket.h`, compiled fine this round) is
  deliberately left alone. The hide opens AFTER the libc header so the
  libc copy keeps its real name; only kernel copies land under the alias.
  Unconditional, no platform macro (no PF5 concern), idempotent via the
  hidden-marker check, applied to both source and build trees.
- No test/dependency-graph change: ethtool `stdint.h` half unchanged,
  same private static libdaemon URL+sha256, no requires() restore, no
  assertion removal, upstream audit unchanged (no_tests, total 0),
  smoke.sh markers untouched. Validation left to HMBS preflight rerun.

## Fix iteration (16th round: interface.h tentative definitions -> extern, link duplicate)
- Comparison with last round (different strategy required): rounds 13-15
  fixed preprocessing/compile (`__uint*_t` via stdint.h, sockaddr_storage
  redefinition via TU-wide macro-rename hide; log proves `ifplugd.c` then
  `interface.c` compile). This round fails at LINK: `ld.lld: duplicate
  symbol: interface_do_message` + `interface_auto_up` (`ifplugd.o` vs
  `interface.o`). Repeating header-hide or flag tweaks would be the
  prohibited same-strategy retry -- the blocker is a new phase (link) with
  a distinct root cause.
- Root cause (tarball-verified): `src/interface.h` carries tentative
  definitions (`int interface_auto_up; int interface_do_message;`) while
  `src/ifplugd.c` defines them (`= 1`) and `src/ifplugstatus.c` defines
  them (`= 0`); `src/interface.c` includes the header. Both binaries link
  `interface.c` plus their main TU (`Makefile.am`: ifplugd = ifplugd.c +
  interface.c + ..., ifplugstatus = ifplugstatus.c + interface.c + ...).
  2004-era GCC defaulted to `-fcommon` (tentatives merged); clang-15
  defaults to `-fno-common` so both objects export strong symbols.
- Fix (root-cause, in `_patch_ifplugd_portability`, source + build trees,
  idempotent via extern check + newline-anchored replace): declare
  `extern int interface_auto_up; extern int interface_do_message;` in
  `interface.h`, leaving exactly one definition per binary in its main TU.
  Chosen over `-fcommon` on purpose: no toolchain-flag dependency,
  portable, matches the standard -fno-common migration (cf. `nlapi.h`
  which already declares `extern int nlapi_fd;`). No other header has this
  pattern (audited all 0.28 headers).
- No test/dependency-graph change: same private static libdaemon
  URL+sha256, no requires() restore, no assertion removal, upstream audit
  unchanged (no_tests, total 0), smoke.sh markers untouched. Validation
  left to HMBS preflight rerun.

## Fix iteration (17th round: conf install-data-local -b -D portable)
- Comparison with last round (different strategy required): rounds 11-16
  moved the build through configure plus compile plus link (private libdaemon
  ready, main configure OK, binaries link), but package() now dies in
  conf/ with `/bin/sh .../install-sh -c -b -D -m755 ifplugd.init
  .../etc/init.d/ifplugd` reporting `install-sh: -b does not exist`
  (Error 1 at conf Makefile:323, autotools.install()). Repeating
  compiler, pkg-config or portability tweaks would be the prohibited
  same-strategy retry: the blocker is purely the install command, not the
  toolchain.
- Root cause (tarball-verified): upstream conf/Makefile.am is the ONLY
  place in 0.28 using GNU install extensions -b plus -D (3 lines under
  install-data-local); the 2004-era install-sh supports only
  -c/-d/-m/-o/-g/-s/-t, so the round-11 global INSTALL to install-sh
  rewrite (needed for toybox install Error 64 on multi-file installs)
  breaks exactly these lines. The -D flag also created sysinitdir plus
  sysconfdir/ifplugd, which automake does NOT auto-create for
  install-data-local, so stripping flags alone is not enough.
- Fix (new _patch_conf_install_portable(), idempotent): rewrite
  INSTALL -b -D to INSTALL plus one portable mkdir_p line under
  install-data-local (mkdir_p is defined in the same Makefile and becomes
  mkdir -p after configure). INSTALL keeps the install-sh -c form so
  -m755/-m644 stay valid. Applied to the pre-configure template
  (conf/Makefile.in, inherited via config.status) and to the generated
  conf/Makefile post-configure in both build branches plus the package()
  defensive re-apply. Private libdaemon scope untouched (no -b -D there).
- No test or dependency-graph change: same private static libdaemon
  URL plus sha256, no requires() restore, no assertion removal, upstream
  audit unchanged (no_tests, total 0), smoke.sh markers untouched.
  Validation left to HMBS preflight rerun.

## Fix iteration (18th round: install-sh -m needs a space)
- Comparison with last round (same conf fingerprint, new layer): round 17
  stripped -b -D and added the mkdir_p line, and the log proves it worked
  (command is now `install-sh -c -m755 ...`, no more -b). The failure moved
  one token forward: `install-sh: -m755 does not exist` (conf Makefile:324).
  Repeating the -b -D strip would change nothing; the remaining blocker is
  the attached mode form.
- Root cause: upstream writes `-m755`/`-m644` (valid for GNU install); the
  2004-era install-sh parses `-m` as `-m) chmodcmd="chmod $2"` with two
  shifts, so `-m755` matches no case branch and falls through to a filename
  (`-m755 does not exist`). Standard automake INSTALL_DATA lines use
  `-m 644` with a space and never hit this.
- Fix (same _patch_conf_install_portable, extended, idempotent): after the
  -b -D strip, normalize `$(INSTALL) -m<digit>` to `$(INSTALL) -m <digit>`
  via regex. Guard now also triggers on already-patched (no -b -D, still
  attached -m) trees and is anchored on `install-data-local: ifplugd.init`
  so no other Makefile is touched.
- No test or dependency-graph change: same private static libdaemon,
  upstream audit unchanged (no_tests, total 0), smoke.sh markers untouched.
  Validation left to HMBS preflight rerun.

## Fix iteration (19th round: no-tests manifest wiring, evidence gate)
- Comparison with last round (different failure domain): build, package and
  both consumer markers now pass on device (preflight reaches the evidence
  stage: test_package 6/6, `HMBS_TEST_PACKAGE_RESULT` and
  `HMBS_UPSTREAM_TEST_RESULT` markers both emitted and well-formed), but
  the gate reports `incomplete` at stage `evidence` with reason
  `no_tests/0 not allowed because the manifest indicates upstream has
  tests`. Nothing in the compile, install or test logic changed; the
  blocker is purely the declaration wiring in `test_package/MANIFEST.yml`.
- Root cause: `upstream_check_command` held the descriptive string
  `"make check (automake-generated no-op; ...)"`. The HMBS lister treats
  any non-empty check command as "upstream has tests" and rejects a
  `no_tests`/0 verdict (documented precedent: inspircd 4.7.0 MANIFEST
  comment "Must stay empty ... rejects no_tests/0"; sibling ifmetric 0.3,
  same 0pointer family, uses `""`). `upstream_test_count_method:
  autotools_tests` sent the same false signal (it names a TESTS
  enumeration, but there is nothing to enumerate).
- Fix (manifest only, no code/test change): `upstream_check_command: ""`
  with the explanation moved to a comment; `upstream_test_count_method:
  manual_audit` (total 0 comes from the manual tarball + Makefile.am
  audit above, matching indelible 1.03 precedent for autotools no-tests
  packages). `upstream_tests_exist: false` + non-empty
  `upstream_test_audit`, `upstream_test_total: 0`,
  `upstream_test_in_build: false`, `upstream_test_command: ""` and
  `upstream_tests: []` unchanged. `smoke.sh` markers untouched (the
  no-tests marker is already emitted from the consumer test on-device in
  both pass and fail paths, per the libofa precedent). No assertions
  removed, no tests skipped, no dependency change.
  Validation left to HMBS preflight rerun.
