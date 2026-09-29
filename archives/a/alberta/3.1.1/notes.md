# alberta 3.1.1 OpenHarmony adaptation

## Source

Upstream ALBERTA (adaptive multi-level finite element toolbox) 3.1.1,
taken as the pristine `alberta_3.1.1.orig.tar.bz2` from the Debian
official pool (byte-identical to the upstream 3.1.1 release; the
upstream download site is unreachable and the upstream GitLab archive
needs sign-in). SHA256 matches the signed Debian `.dsc` record.

## Adaptation

- Bootstrap in build(): `generate-alberta-automakefiles.sh` (generates
  per-dimension Makefile.am from the template) then
  `autoreconf --force --install`; automake 1.18 / libtool 2.5.4 arrive as
  bare tool_requires (no autoconf/m4 edge); autoreconf runs from the
  worker native suite via a merged PATH, not the scrubbed conanbuild env.
- Configure for OHOS: `--disable-graphics` (no X11/OpenGL/OpenDX/Motif
  on the worker), `--disable-debug` (same as upstream CI debian jobs),
  `--disable-waiting-in-tests`, explicit
  `--build/--host=aarch64-unknown-linux-ohos` (uname reports HarmonyOS).
- Hard dependency `libtirpc/1.3.7` (rpc/xdr mesh I/O) from the ohpcd
  registry; AutotoolsToolchain forwards its flags to configure probes.
- HMDFS workaround: rewrite `umask 077` to `umask 022` in the generated
  configure (same as the libtirpc/adcli recipes); serialized `make -j1`.
- Upstream `make check` runs in build() and every test-suite.log is
  aggregated into the HMBS_UPSTREAM_TEST_RESULT marker (PASS+XFAIL count
  as passed, FAIL+XPASS+ERROR as failed).
- test_package links libalberta_utilities and checks generate_filename,
  MEM_ALLOC/MEM_FREE and the parameter database round-trip (3 checks).

## Preflight failure 2026-09-27: libtirpc remote shadowing (fixed)

- Symptom: `conan create` died in dependency-graph resolution with
  `ERROR: There are invalid packages: libtirpc/1.3.7: Invalid:
  libtirpc/1.3.7 is only supported on Linux and FreeBSD`.
- Root cause: the true-machine preflight checks conancenter before ohpcd
  (official CI disables conancenter, see `ci/conan/setup.sh`), so the bare
  `libtirpc/1.3.7` requirement resolved to the conancenter recipe revision
  `dce759ee...`, whose `validate()` rejects OHOS. Verified against the
  upstream source: alberta's `configure.ac` hard-requires tirpc
  (`AC_CHECK_LIB([tirpc],[rpc_call],...AC_MSG_ERROR)`), so the dependency
  cannot be dropped.
- Fix: RREV-pin the requirement to this repo's OHOS-compatible recipe on
  ohpcd — `libtirpc/1.3.7#ffaa36790004ab5a69233aef6f108319` (single ohpcd
  revision, published 2026-08-24 with the merged libtirpc/1.3.7 recipe;
  confirmed via the ohpcd Conan v2 revisions API). Same pattern as the
  abuild-sudo/openssl and bzrtp/sqlite3 recipes. `manifest.yaml`
  dependencies updated in sync.

## Preflight failure 2026-09-27 (round 2): conancenter m4 built from source (fixed)

- Symptom: dependency graph now resolves (libtirpc pin worked — log shows
  `Checking remote: conancenter` then `Checking remote: ohpcd`), but the
  build dies compiling the `m4/1.4.19` tool package: its `configure[139]`
  reports `/data/service/hnp/bin/bash: inaccessible or not found`,
  Error 127. Different failure domain from round 1 (graph Invalid ->
  tool-package build failure), so a different fix applies.
- Root cause: something in the closure (ohpcd autoconf) pulls `m4` bare,
  which resolves to the conancenter recipe
  (`patches/1.4.19-0004-disable-hardening-in-source.patch` in the log is
  the CCI patch name). The CCI recipe runs upstream configure unchanged;
  autoconf-generated configure re-execs itself through a non-empty
  `CONFIG_SHELL`, and the profile value
  `/data/service/hnp/bin/bash` is inaccessible on this worker
  (zurl/1.12.0 notes #30, same `configure[139]` signature). This repo's
  own m4/1.4.19 recipe (ohpcd revision `9a84a566`, 2026-08-05) verifies
  shell existence/access before trusting `CONFIG_SHELL` (`_select_shell`)
  and carries OHOS triplet/tempdir patches.
- Fix: pin the whole autoreconf tool chain to the ohpcd hardened
  revisions in `build_requirements()` — automake/1.18#65a7ba60,
  libtool/2.5.4#fe9f8e73, autoconf/2.72#ded5821b (all single ohpcd
  revisions per the v2 API; automake/libtool already resolved from ohpcd
  in prior logs) — plus `m4/1.4.19#9a84a566` with `override=True` to
  unify the transitive bare-m4 node (heimdal/7.8.0 precedent).
  `manifest.yaml` gains the matching `build.build_requirements` list.

## Preflight failure 2026-09-27 (round 3): CCI m4 still built, own-layer shell hardening

- Comparison: round-2's build-context-only
  `tool_requires("m4/1.4.19#9a84a566", override=True)` did not capture the
  failing node — the round-3 log still applies the CCI patch
  `1.4.19-0004-disable-hardening-in-source.patch` and dies in the CCI
  recipe's `autotools.configure()` (line 110; our repo's m4 recipe has no
  such call). Auditing this repo's `archives/a/autoconf/2.72/conanfile.py`
  shows why: it declares m4 twice — `requires("m4/1.4.19")` (host edge)
  AND `tool_requires("m4/1.4.19")` (build edge), both bare. A
  build-context-only override cannot unify the host-context edge, which
  keeps resolving conancenter-first to the CCI recipe.
- Fix (different from round 2 — dual context + own layer):
  1) `requirements()` gains the host-context twin
     `self.requires("m4/1.4.19#9a84a566238ea69b63e725d646354933",
     override=True)`; the m4 application binary is unused by this
     library's link closure, the pin only forces the hardened ohpcd
     recipe for that node.
  2) Own-layer immunity for the same poison: `generate()` defines
     `CONFIG_SHELL`/`SHELL` in the AutotoolsToolchain environment and
     `build()` exports them into `os.environ` (the bootstrap
     `self.run()` calls use `env="conanbuild"`), both via a new
     `_select_shell()` that only accepts an absolute path after
     existence + exec-bit verification, else HMBS-guaranteed `/bin/sh`
     (ohpcd m4 recipe pattern; zurl notes #30 mechanism). Without this,
     our own autoreconf/configure would die with the identical
     configure[139]/Error-127 signature once the tool chain is fixed.

## Preflight failure 2026-09-27 (round 4): subtraction, not pinning (2nd strategy cycle)

- Why the last three RREV-pin rounds were invalid (same failed assumption):
  all three assumed the failing `m4/1.4.19` node could be captured by
  pinning it to the ohpcd hardened revision `9a84a566`. The round-4 log
  still builds the CCI recipe (`patches/1.4.19-0004-...`, `autotools.
  configure()` line 110 which our m4 recipe does not have), proving the
  pin never took effect. Two compounding causes found by re-reading the
  repo sources: (1) as a `tool_requires`, m4 builds for the Linux build
  context, where our m4 recipe's `_select_shell` hardening is gated behind
  `is_ohos` and never runs — the OHOS-only fix cannot save a Linux-context
  build; (2) the pin set referenced `libtool/2.5.4`, but this repo only
  carries `libtool/2.5.4.1` + `2.4.7`, so that leg resolves CCI anyway and
  the host `requires(m4, override=True)` cannot unify autoconf's dual
  host+build m4 edges. Continuing to pin is prohibited by the 2nd-cycle
  rule.
- Different route (subtraction): follow the merged-recipe precedent
  (`adcli/0.9.2`, `abiword-plugin-*` family, all green with bare
  `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")` and
  NO autoconf/m4 declaration). The HNP worker image natively provides the
  autoconf suite (autoconf/autom4te/m4), so `autoreconf -fi` works without
  any Conan autoconf/m4 edge. This recipe now declares exactly that
  minimal pair (bare, no RREV), deletes both the tool and host m4 pins and
  the autoconf pin, and keeps only the proven-effective libtirpc RREV pin.
  Own-layer `CONFIG_SHELL`/`SHELL` verification (`_select_shell`) is kept
  as defense for our own configure step. test_package no longer defaults
  to the poisoned `/data/service/hnp/bin/bash`; it accepts an absolute
  shell only after existence + exec-bit verification, else `/bin/sh`.

## Preflight failure 2026-09-27 (round 5): autoreconf missing after m4 subtraction

- Symptom: the m4-subtraction round got past the CCI m4 source build, but
  alberta's own `_bootstrap()` now fails with `/bin/sh: autoreconf:
  inaccessible or not found` (build() line 183). This falsifies the round-4
  assumption that the HNP worker image natively provides autoreconf on the
  conanbuild PATH (adcli/abiword comments describe CI, not this preflight
  env which only probes cmake/make/ninja/python3).
- Fix (different from round 4 — add back the single missing edge, still no
  m4): `build_requirements()` becomes the bare triple automake/1.18 +
  autoconf/2.72 + libtool/2.5.4 (no RREV, no m4). Bare lets conan reuse a
  published autoconf binary instead of forcing a source build that would
  need m4; the autoconf runtime locates a working m4 without a Conan m4
  edge. `_bootstrap()` now resolves the binary via `_find_autoreconf()`
  (conanbuild PATH first, then native absolute fallbacks, then tool-b package
  bindirs) instead of assuming PATH. `manifest.yaml` synced.

## Preflight failure 2026-09-27 (round 6): bare autoconf reintroduces CCI m4 — merged-PATH bootstrap instead

- Symptom: round-5's bare `tool_requires("autoconf/2.72")` reproduced the
  IDENTICAL CCI m4 failure (same patch `1.4.19-0004-...`, same package ID
  `579a4b17...`, same poisoned `/data/service/hnp/bin/bash` at
  configure[139]). This falsifies the round-5 assumption that a bare
  autoconf reuses a binary: any Conan autoconf edge pulls a bare m4 that
  resolves conancenter-first, and its Linux build-context configure dies
  on the profile-poisoned CONFIG_SHELL that only the consumer's own env
  can sanitize, never a dependency's build.
- Fix (different from round 5 — no dependency-graph change at all, only
  the run environment): keep the round-4 m4-free graph (bare automake +
  libtool, proven to get past the m4 build) and fix round-4's
  `autoreconf: not found`, which was caused by `env="conanbuild"`
  scrubbing the outer PATH. `_bootstrap()` now composes
  `_merged_bootstrap_path()` (Conan tool bindirs + /data/service/hnp/bin
  native suite + HMBS tool dirs + outer PATH) with sanitized
  CONFIG_SHELL/SHELL/TMPDIR in os.environ and runs both bootstrap steps
  with the default inherited env. `manifest.yaml` back to the two-entry
  list.

## Preflight failure 2026-09-27 (round 7): autoreconf exists but is not directly executable — interpreter fallback instead

- Why the round-6 merged-PATH fix was invalid (same failed assumption):
  round 6 assumed `autoreconf: not found` meant PATH composition (that
  dropping env="conanbuild" and hand-merging bindirs + native dirs would
  reveal the binary). The round-7 log falsifies it: the identical
  `/bin/sh: autoreconf: inaccessible or not found` (build() line 259)
  recurs WITH the merged PATH already containing every candidate dir
  (tool bindirs, /data/service/hnp/bin, HMBS tool dirs, outer PATH).
  The HMBS wording "inaccessible or not found" (not plain ENOENT) plus
  HMBS_PLATFORM_CAPABILITIES hardlink=0/chmod=0 points at existence
  without executability: HMDFS denies chmod, so the native perl script
  can be present without +x, and both `shutil.which` and the old
  `os.access(X_OK)` gate silently discard it before the fallback bare
  `autoreconf` dies in /bin/sh. Continuing to reshuffle PATH is
  prohibited by the 3rd-cycle rule.
- Different route (no dependency-graph change at all, only invocation +
  buildenv materialization): keep the proven m4-free graph (bare
  automake + libtool), and (1) probe autoreconf candidates by existence
  (isfile, no exec-bit gate: tool bindirs, then native absolute paths,
  then which-hits); (2) invoke each candidate through a fallback chain
  (direct, then `perl <cand>`, then `sh <cand>`) so a non-executable
  perl script still runs; (3) hand-materialize the two buildenv pieces
  bootstrap needs but only env="conanbuild" would provide (ACLOCAL_PATH
  from tool share/aclocal* + hnp sysroots, PERL5LIB for automake
  Config.pm, M4 default) while keeping sanitized CONFIG_SHELL/SHELL in
  os.environ — env="conanbuild" itself stays dropped because it
  re-injects the poisoned CONFIG_SHELL; (4) failure now raises a
  diagnostic quoting the searched bindirs plus an `ls` of the native
  suite (mode/size of auto*/m4/perl) so the next round has file-level
  evidence instead of PATH guesses.

## Preflight failure 2026-09-27 (round 8): full Conan toolchain + inline-env autoreconf (E178/apertium pattern)

- Why the round-7 route was invalid (different failure, new evidence):
  round 7's existence probe returned file-level proof instead of a fix:
  `bindirs=[autom.../p/bin, libto.../p/bin]` (only automake+libtool, as
  expected — autoreconf ships with autoconf), `/data/service/hnp/bin:
  No such file or directory`, `/storage/.../usr/local/bin: no
  auto*/m4/perl entries`. The adcli-era "native autoconf suite" does not
  exist on this sandbox, so every native fallback was dead code. At the
  same time the local tarball audit (864 files) confirmed autoreconf is
  unavoidable: `configure.ac` (AC_PREREQ 2.69, PKG_PROG_PKG_CONFIG,
  LT_INIT) + `m4/*.m4` + `generate-alberta-automakefiles.sh` are present,
  no generated `configure` — upstream's own `fromsvnreconf.sh` runs
  exactly generate-script + `autoreconf --force --install`.
- Different route (dependency graph + invocation, never tried together):
  adopt the merged-green apertium 3.9.12 pattern for this exact
  signature (release tarball without configure): bare
  `tool_requires(automake/1.18, autoconf/2.72, libtool/2.5.4)` plus an
  explicit `m4/1.4.19` edge (without it the transitive bare m4 resolves
  conancenter-first) plus `pkgconf/3.0.5` (pkg.m4 + pkg-config binary
  for PKG_PROG_PKG_CONFIG/PKG_INSTALLDIR); no RREV pins. autoreconf runs
  under env="conanbuild" with command-inline overrides only
  (`CONFIG_SHELL/SHELL` pinned to the verified shell,
  autoconf/m4 bindirs prefixed to PATH, discovered aclocal dirs,
  `PERL=perl` + PERL5LIB converged to the two pure-perl share dirs,
  writable TMPDIR trio) — inline because conanbuild re-injects the
  profile-poisoned CONFIG_SHELL at run time. Residual risk admitted:
  m4/autoconf/perl tool packages must resolve to binaries (no source
  build survives the dangling CONFIG_SHELL); automake+libtool already
  proved binaries flow on this sandbox.

## Preflight failure 2026-09-27 (round 9): vendor m4+autoconf at build time, zero autotools edges

- Why the round-8 route was invalid (same fingerprint, 3rd occurrence):
  the full triple + explicit bare m4 reproduced the IDENTICAL CCI m4
  source build (patch 1.4.19-0004, configure[139] vs dangling
  /data/service/hnp/bin/bash, package ID 579a4b17, line 110). Asymmetry
  analysis explains it: automake/libtool/autoconf have no CCI
  competition so bare versions fall through to ohpcd binaries, but bare
  m4 always resolves conancenter-first and its Linux build-context
  configure dies on the profile poison — and no recipe-level env can
  sanitize a dependency's own build (profile buildenv wins over outer
  env). Pinning (rounds 2-3) is prohibited to repeat.
- Different route (never tried: dependency graph goes m4-free AND no
  native assumption): build_requirements is only the proven-binary trio
  automake + libtool + pkgconf; m4 1.4.19 + autoconf 2.72 release
  tarballs are downloaded (URL order = repo GNU mirror mapping,
  sha256 identical to repo conandata, verified context with unverified
  fallback) and built into a private build-folder prefix under this
  recipe's own sanitized env, then the vendored `perl autoreconf`
  runs on the plain process env (never env="conanbuild"). New worker
  requirements are explicit and probed with evidence: a build-machine
  cc (cc/gcc/clang) for the m4 build, and a system perl passing the
  -MCwd load test (the exact XS module that breaks conan perl).
  Missing cc/perl fails fast naming every probed path — that outcome
  would convert this from a recipe issue into documented toolchain
  evidence (dangling CONFIG_SHELL + absent hnp mount + no cc/perl).


## Preflight failure 2026-09-27 (round 10): inline env + build-cc disambiguation (4th strategy cycle)

- Why the round-9 vendored route was invalid (same fingerprint, new
  location): the vendored m4 configure died with the IDENTICAL
  `configure[139]: /data/service/hnp/bin/bash: inaccessible or not
  found` -- inside OUR OWN vendor build (`CC=/storage/.../.harmonybrew/
  bin/cc`, `"/bin/sh" ./configure`). This falsifies round 9's core
  assumption that "os.environ sanitization + bare self.run keeps the
  profile poison out of the vendored build". Two independent vectors
  found by re-reading the failure against repo sources: (A) run-time
  conanbuild aggregation (profile buildenv carrying the poisoned
  CONFIG_SHELL) overrides the process env at self.run time, so
  os.environ assignments never reach the configure re-exec; (B)
  `_find_build_cc` preferred PATH-resolved `cc`, i.e. the harmonybrew
  OHOS cross-compiler wrapper -- wrong twice over for a tool that must
  EXECUTE on the x86_64 worker (possible own dependency on the
  inaccessible bash, plus a cross-built m4 binary could never run under
  autoreconf). 4th-cycle compliance: no pin (rounds 2-3), no native
  assumption (rounds 4/6/7, disproved by file evidence), no Conan
  autoconf/m4 edge (rounds 5/8, CCI competition), no os.environ-only
  reshuffle (rounds 6/9, disproved this round). New mechanism, new
  commands, new evidence gates.
- Fix (different route -- what reaches the command, not the process):
  1) new `_inline_prefix()`/`_shq()`/`_compose_bootstrap_path()`
  helpers; EVERY vendor/bootstrap self.run command (m4/autoconf
  configure, make, install, generate-script, `perl autoreconf`, all
  cc/perl probes, vendored-m4 smoke test) now carries shell-inline
  `CONFIG_SHELL/SHELL/TMPDIR(+CC/PATH/PERL/M4/PERL5LIB/ACLOCAL_PATH)`
  assignments that override any aggregated export for that invocation
  (self.run executes through a shell; `cd .. && ..` chaining in repo
  recipes proves it). os.environ composition is kept as defense in
  depth only. 2) `_find_build_cc()` now prefers system build-machine
  compilers (/usr/bin/cc|gcc|clang), defers any `.harmonybrew` wrapper
  to last resort, and smoke-gates each candidate with a sanitized
  `cc --version` probe. 3) `_build_vendor_tool()` adds MAKEINFO=true
  (same as this repo's autoconf recipe) and a single-top-dir guard on
  the tarball. The existing vendored-m4 `--version` execution smoke
  test remains the final gate before autoreconf.
- Evidence kept for next round: `vendored toolchain CC: <path>
  (<probe trail>)` names the winning compiler; any remaining
  `configure[139]` failure now cannot be the aggregation leak (inline
  prefix is on the command line in the log) and must be diagnosed from
  the new location.

## Preflight failure 2026-09-27 (round 11): vendored m4 config.guess cannot identify HarmonyOS

- Symptom: with the round-10 inline-env fix the vendored m4 configure is
  reached, but dies in `build-aux/config.guess: unable to guess system
  type` -> `configure: error: cannot guess build type` (config.guess
  version 2021-05-24, shipped in m4 1.4.19). New failure domain
  (config.guess identification, not CONFIG_SHELL poisoning).
- Root cause: the vendored tools are native builds that must execute on
  the HarmonyOS worker itself, but the old config.guess predates the
  HongMeng kernel uname and has no HarmonyOS/OHOS case, so guessing can
  never succeed there regardless of shell sanitization.
- Fix: `_build_vendor_tool()` now passes explicit native
  `--build=<triplet> --host=<triplet>` to every vendored configure,
  bypassing config.guess (old config.sub accepts *-linux-gnu). The
  triplet comes from a new `_vendor_build_triplet()` helper: `cc
  -dumpmachine` from the already-selected build-machine cc, falling back
  to `platform.machine()-pc-linux-gnu`; ohos/harmony outputs are
  rejected so a cross binary can never be built for a tool that must run
  on this worker. No test-count or dependency-graph change.

## Preflight failure 2026-09-27 (round 12): vendored autoconf cannot find vendored m4

- Symptom: with the round-11 triplet fix the vendored m4 builds and
  installs, but the vendored autoconf 2.72 configure dies with
  `checking for GNU M4 that supports accurate traces... configure:
  error: no acceptable m4 could be found in $PATH`. New failure domain
  (vendor PATH wiring, not config.guess or CONFIG_SHELL).
- Root cause: `_build_vendor_tool()` composed PATH from
  `_compose_bootstrap_path()` (Conan tool bindirs + HMBS/system dirs +
  outer PATH) which never contains the private vendor prefix bin; the
  worker has no system m4 (round-7 file evidence:
  `/storage/.../usr/local/bin: no auto*/m4/perl entries`), so the
  just-installed `prefix/bin/m4` is invisible to the autoconf probe.
- Fix (no graph change, vendor PATH only): if `prefix/bin` exists it
  leads the composed PATH via the existing `extra_first` parameter
  (harmless when empty for the first tool, decisive for the second);
  additionally, when `prefix/bin/m4` already exists its absolute path
  is exported inline as `M4` for that configure invocation. No test
  counting or dependency change.

## Preflight failure 2026-09-27 (round 13): Conan aclocal wrapper broken -- vendor automake too

- Symptom: with m4 + autoconf vendored and installing cleanly, the final
  `perl <vendor>/bin/autoreconf --force --install` dies in the *Conan*
  automake tool package's `bin/aclocal` wrapper:
  `aclocal[8]: .../p/bin/.aclocal-real: No such file or directory`,
  `autoreconf: error: .../aclocal failed with exit status: 126`
  (build() line 1090). New failure domain (foreign tool binary, not our
  vendor build or shell sanitization).
- Root cause: that ENOENT fires in one of two ways, both properties of
  the published automake binary that no consumer env can repair --
  (a) the relocatable-packaging wrapper (`_make_relocatable` in
  `archives/a/automake/1.18/conanfile.py`, which `os.replace`s the real
  perl script to `.aclocal-real`) lost its hidden file at publish time,
  or (b) the hidden perl script exists but its baked-in `#!` interpreter
  path does not exist on this worker (same dangling-interpreter family
  as the CONFIG_SHELL poisoning). Either way `aclocal` can never exec.
- Fix (same vendoring strategy, extended by one tool -- no graph change):
  `_VENDOR_AUTOMAKE` (official GNU 1.18 tarball; URL order = repo GNU
  mirror mapping tuna -> ustc -> aliyun -> origin; sha256 identical to
  `archives/a/automake/1.18/conandata.yml`, never altered) is built into
  the same private prefix after autoconf. Vendor bin already leads PATH
  in `_bootstrap`, so the vendored aclocal shadows the broken wrapper;
  the automake vendor configure gets `PERL` pinned to the probe-verified
  perl, installed aclocal/automake shebangs are rewritten to that perl
  (`_normalize_vendor_perl_shebangs`), vendor automake share dirs join
  PERL5LIB/ACLOCAL_PATH, and aclocal + automake join the `--version`
  smoke gate. Conan edges unchanged (automake/libtool/pkgconf trio kept
  for macro dirs), so `manifest.yaml` is untouched.

## Preflight failure 2026-09-27 (round 14): autoreconf bypasses PATH via $ACLOCAL -- pin tool vars

- Comparison (2nd occurrence of the aclocal-126 fingerprint, different
  route required): round 13 assumed vendor/bin leading PATH suffices to
  shadow the broken Conan aclocal wrapper. The new log falsifies it:
  the vendored automake built and installed cleanly (`.vendor/share/
  automake-1.18/install-sh` chmod lines; PERL5LIB/ACLOCAL_PATH contain
  the vendor automake share dirs), the `--version` smoke tests passed
  (failure is at the later autoreconf line, build() 1234 <- _bootstrap
  1204), yet autoreconf still exec'd
  `.../autom3efab95d532f9/p/bin/aclocal` with the identical
  `.aclocal-real: No such file or directory` / exit 126. An executable
  vendor aclocal first on PATH cannot lose a PATH lookup, so the
  selection bypassed PATH.
- Root cause: $ACLOCAL/$AUTOMAKE. This repo's automake recipe exports
  both as absolute buildenv paths (`buildenv_info.define_path`), the
  run-time conanbuild aggregation re-injects them at self.run time
  (round-10 mechanism), and autoreconf honors $ACLOCAL/$AUTOMAKE (like
  $AUTOCONF/$AUTOHEADER/$AUTOM4TE) over PATH lookup. Our inline prefix
  overrode PATH/PERL/M4/PERL5LIB/ACLOCAL_PATH but never these tool
  vars, so the leaked absolute path to the broken wrapper won.
- Fix (no graph change, invocation only): the autoreconf inline prefix
  now pins ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER/AUTOM4TE to the
  vendored binaries (existence-gated, falls back to PATH when absent),
  mirrored into os.environ as defense in depth; each pin is logged
  (`autoreconf tool pinned: ...`). libtoolize is deliberately left to
  PATH: the Conan libtool binary is the proven-binary leg with no
  breakage evidence, and evidence-free changes are out of scope.

## Verification

- `make check`: 28 registered upstream cases (15 of them upstream XFAIL
  entries); real HarmonyOS counts pending first preflight.
- `test_package/test_alberta`: 3/3 checks designed; real run pending
  first preflight.

## Preflight failure 2026-09-27 (round 15): main-tree configure guard (this round)

- Symptom: vendored m4/autoconf/automake now build and `autoreconf --force
  --install` succeeds, but alberta's OWN configure dies with the familiar
  `configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`
  (Error 127 at `autotools.configure()`, build() line 1270). New location
  (main tree, not vendor), same fingerprint.
- Root cause: `ci/conan/profiles/ohos-aarch64` [buildenv]
  `CONFIG_SHELL=/data/service/hnp/bin/bash` is absent on this preflight
  worker. generate() already defines CONFIG_SHELL/SHELL via
  AutotoolsToolchain.environment() and build() exports a verified shell
  into os.environ, but this round proves BOTH lose to run-time conanbuild
  aggregation (profile buildenv wins at helper time -- round-10 mechanism,
  now in the main tree where shell-inline prefixes are unavailable because
  the Autotools helper builds its own command).
- Fix (winning layer = the script itself, not env): new
  `_sanitize_configure_config_shell()` inserts an idempotent
  HMBS_CONFIG_SHELL_GUARD right after the shebang that resets a
  non-executable $CONFIG_SHELL to the verified shell before autoconf's
  re-exec block (line ~139) is reached; `_sanitize_all_configures()`
  applies it to source/build configure copies. Called both at the end of
  `_bootstrap()` and immediately before `autotools.configure()`. Zero
  behavior change on healthy workers (guard is a no-op when the
  configured shell is executable). No graph/test-count change.

## Preflight 2026-09-27 (round 17): SSH transport close at config.status tail (this round)

- Symptom: configure probes all pass (malloc/lstat/rename-hardlink-guess-no/
  pthread_sigmask/putenv/sched_yield), `config.status: creating po/Makefile`
  (then examples/Makefile, lib/config.h) emits, then
  `Connection to 47.242.172.160 closed by remote host`. No recipe assertion,
  no compiler error, no HMBS platform-diagnosis code; upstream markers stay
  0/0/0 because `make -j1`/`make check` were never reached. Prior guards all
  held (no configure[139], no config.guess error, no freadahead error, no
  aclocal-126 in this log).
- Diagnosis: transport-level drop at the very end of configure, not a
  deterministic recipe failure. Minimal hardening only, no test-semantics
  change: `generate()` adds `--disable-nls` (log-anchored on the po/Makefile
  + `checking for a traditional french locale` gettext probes). NLS only
  ships translated messages; po/ carries no TESTS so the 28 upstream counts
  and the 3 test_package checks are unaffected. If the flag is unsupported
  configure only warns. Effectiveness is judged by the next preflight; a
  repeated bare `Connection closed` with no recipe error is infra, not code.

## Preflight 2026-09-27 (round 18): profile-pinned CC absent, compiler fallback

- Symptom: main configure dies with checking for
  aarch64-unknown-linux-ohos-gcc as /data/service/hnp/bin/clang then
  C compiler cannot create executables (Error 77 at autotools.configure);
  helper evidence is CC probe failed with Errno 2 No such file or directory.
  New failure domain (cross-compiler path, not shell or config.guess).
- Root cause: the ohos-aarch64 profile pins compiler_executables to
  /data/service/hnp/bin/clang, absent on this preflight host. The round-16
  PATH restore assumed the hnp dir exists; this log falsifies it. Same
  domain as bwm 0.6.3, bzrtp 5.3.105 and zurl 1.12.0.
- Fix (no graph or test change, env only): new _resolve_ohos_compiler
  (conf value when isfile, else PATH plus harmonybrew/SDK/hnp/usr-local
  candidate dirs, pure isfile, only CC/CXX) wired at three layers:
  generate env.define, build-scope save_script after tc.generate, and
  build os.environ export. Healthy CI keeps the profile path unchanged.

## Preflight 2026-09-27 (round 19): tirpc bare-check needs explicit search paths

- Symptom: with the round-18 compiler fallback every compiler check passes
  (harmonybrew clang/clang++ through static-flag probes), but configure dies
  at checking for rpc_call in -ltirpc as no, then configure error no tirpc
  library exiting (Error 1 at autotools.configure). Different failure domain
  from round 18 (dependency-flag wiring, not compiler availability), so a new
  fix applies and nothing from round 18 is reverted.
- Root cause: upstream uses a bare AC_CHECK_LIB for tirpc (no pkg-config),
  which only succeeds when -I/-L reach it. The toolchain merge alone did not
  deliver them on this host.
- Fix (no graph or test change): generate wires -I include and include/tirpc
  plus -L lib from the resolved libtirpc package folder into
  tc.extra_cflags/extra_ldflags (ypserv 4.2 pattern, idempotent when already
  present). Evidence dump now probes the actually-used resolved CC and adds
  the config.log tirpc section with the real linker error.

## Preflight 2026-09-27 (round 20): triple-layer tirpc flags (this round)

- Symptom: same `checking for rpc_call in -ltirpc... no` ->
  `configure: error: no tirpc library, exiting` recurs AFTER the round-19
  fix, and the config.log conftest line
  `clang -o conftest -O3 -DNDEBUG conftest.c -ltirpc -lm` carries NO -L
  flag. This falsifies the round-19 assumption that the toolchain layer
  (tc.extra_cflags/extra_ldflags) alone reaches the conftest: -ltirpc in
  the link line comes from LIBS hardcoded by AC_CHECK_LIB, not from Conan,
  so the absent -L proves the toolchain layer lost to run-time conanbuild
  aggregation on this host (same leak family as rounds 10/14/15/18).
- Fix (no graph or test-count change, env layers only): new
  `_tirpc_search_flags()` helper (existing-dir -I for include/include/tirpc,
  -L for lib+lib64, plus libtirpc.a/.so listing as evidence) wired at all
  three layers -- (1) tc.extra_* (kept), (2) env.append CFLAGS/CPPFLAGS/
  LDFLAGS in generate() (epic5/3.0.3 pattern), (3) build-scope save_script
  append plus build() os.environ append (bwm/0.6.3 winning layer). Healthy
  CI unchanged (flags idempotent when aggregation already delivers them).

## Preflight 2026-09-27 (round 21): main-tree mktemp shadow + failure-first evidence (this round)

- Log attribution (no graph change): the `dirname-lgpl.o`/`stripslash.o`
  compiles in the stdout tail are the *vendored m4* gnulib build, not
  alberta (verified: alberta's tree has no such files; m4 1.4.19 gnulib
  does). The main-tree `autotools.configure()` Error 1 therefore carries
  no visible main-configure output in the summarized log.
- Source audit (upstream `alberta3` configure.ac, main branch): after the
  tirpc checks the only remaining `AC_MSG_ERROR` is
  `AC_CHECK_FUNCS([strdup xdr_int32_t xdr_int64_t xdr_int])` ("Sorry,
  these are needed.."). The symbols were verified present in libtirpc
  1.3.7 (Debian `+ds.orig` audit: `tirpc/rpc/xdr.h` declares all four,
  `src/xdr.c` implements them, `src/libtirpc.map` exports them), and the
  link environment is the round-20 triple layer that already got past
  `AC_CHECK_LIB([tirpc])`, so a funcs-link failure has no mechanism left.
- Prime suspect instead: `AC_CONFIG_COMMANDS([dof_free_bit.h])` runs
  `AS_TMPDIR` at config.status time -- the exact `[unsafe_local_mktemp]`
  family (mktemp-made dir not writable afterwards). The vendored tool
  builds already carry the mktemp fallback shadow; the main tree never
  did, so a config.status-tail failure fits the Error-1-with-passing-checks
  signature.
- Fix (no graph / test-count / flag-semantics change): (1) the main-tree
  configure gets the same probe-gated mktemp shadow
  (`_mktemp_fallback_wanted(self.build_folder)`), exposed through a
  build-scope `save_script("alberta_mktemp_shim")` PATH prepend (round-18
  winning channel) plus a `build()` os.environ PATH mirror (cyrus-sasl-*
  precedent; healthy workers keep an unshadowed PATH); (2) the evidence
  dump now leads with a compact `HMBS_CONFIGURE_FAILURE` block (exact
  `configure: error` line + last check + 25 lines of context, <=2.5k
  chars) so the true error survives log summarization next round.


## Preflight 2026-09-27 18:00 (round 22): same fingerprint, different strategy (this round)

- Comparison (2nd occurrence, strategy must differ -- no repeat of the
  round-21 environment shadow): the 18:00 preflight ran *with* the
  round-21 tree (traceback line moved 1803 -> 1898 by those insertions
  themselves) and failed identically -- same `autotools.configure()`
  Error 1, same post-obstack position. New evidence in this log: a
  conftest link line now carries `-L<libtirpc>/lib` x3, i.e. the
  round-20 triple layer provably delivers search paths, and the xdr
  symbols were already verified present -- so the checks phase has no
  remaining fatal mechanism in configure.ac, yet the exact error line
  is still swallowed by summarization (the round-21 warning block did
  not surface either).
- Different route (failure propagation, not environment): new
  `_configure_failure_summary()` reads config.log at failure time and
  embeds the exact `configure: error` line + the last `checking` line
  + the round-21 mktemp shadow state (on/off/built-but-off-PATH) into
  the raised `ConanException` text -- the one channel every preflight
  summary preserves verbatim (proven by both rounds traceback lines).
  No new env shadowing, no flag/test change; pure log-reading. The next
  round will therefore see either the true failing check (act on it) or
  `mktemp_shadow=off` (revisit activation) / `on` (kill the mktemp
  theory) instead of re-guessing.

## Preflight 2026-09-27 18:23 (round 23): forensics fix plus RM pin (this round)

- Comparison (3rd occurrence, strategy must differ again): round 22 verdict
  surfaced via the exception channel -- `error line not found in config.log`
  + `mktemp_shadow=off`. Two consequences: (a) the discovery walk could have
  read a healthy *vendored* config.log first (arbitrary dir order), so every
  prior config.log reading is suspect; (b) with all checks passing and no
  config.log error, the death is almost certainly in the config.status phase
  (files/commands), whose errors reach stdout only. Upstream script audit
  (GitLab main): `install-pkgheader.sh` is `ln -sf` (symlink=1, ln proven
  runnable), `mkdoffreemasks.sh` is exit-status-safe, the generate script is
  proven by successful autoreconf -- leaving `packageheaders` leading
  `${RM} -rf include` as the prime suspect: RM is substituted by no macro in
  configure.ac, so empty or a broken worker shim both kill config.status.
- Fix (new family -- script-layer determinism, not env shadowing): (1) new
  `_find_main_config_log()` (build-release first, never dot-dirs) used by
  both the verdict and the evidence dump; (2) verdict gains phase forensics
  anchored at the log dir (config.status file? generated Makefiles count?
  config.h? config.log tail) to separate checks-phase from config.status
  death next round; (3) new `_pin_packageheaders_rm()` rewrites the
  `${RM}` token to the probe-verified absolute rm in every configure copy
  (hooked into `_sanitize_all_configures`, same generated-file category as
  the umask/CONFIG_SHELL guards; safe on all branches: healthy `rm -f`
  stays equivalent). No flag/test-count change.

## Preflight 2026-09-27 18:44 (round 24): upstream audit + stdout replay (this round)

- Comparison (4th occurrence of the same Error-1 fingerprint, strategy must
  differ again -- 6th policy cycle bans repeating mktemp shadow / exception
  text / RM pin): round 23 forensics pinned the death to
  `log=main|no-error-line|config.status=yes makefiles=67 config.h=yes`,
  `tail=[configure: exit 1]`, `mktemp_shadow=off`. Two falsifications:
  (a) the mktemp theory is dead -- the probe gate left the shadow OFF and
  the failure is identical, so unwritable-mktemp dirs cannot be the cause;
  (b) config.log is proven to be the wrong artifact -- a checks-phase death
  always writes `configure: error`, and 67 generated Makefiles + config.h
  prove the checks phase plus most of config.status already succeeded.
- Upstream audit (Debian `alberta_3.1.1.orig.tar.bz2`, 864 files,
  `configure.ac:958`): the tail is
  `AC_CONFIG_COMMANDS([packageheaders],[${RM} -rf include; for m in ...;
  ${MAKE-make} ... install-pkgincludeHEADERS ...])` with
  `INSTALL_HEADER=install-pkgheader.sh` (bare `ln -sf`, no mkdir). Any
  failure inside that find/sub-make/ln loop kills config.status AFTER the
  files exist -- exactly the observed forensics -- and its message reaches
  stdout only, never config.log. Prior rounds never looked at stdout.
- Fix (new family -- stdout replay + callee hardening, no env/token
  change): (1) new `_replay_config_status()` re-executes the already
  generated `./config.status` via subprocess after failure and embeds
  `rc + find/grep/make availability + 25-line tail` (<=1200 chars) in the
  raised exception text, the channel every summary preserves; (2) new
  `_harden_install_pkgheader()` adds an idempotent DST `mkdir -p` to
  `install-pkgheader.sh` (source+build copies), self-sufficient even if
  automake MKDIR_P is degraded on HMFS (chmod=0 caps). Healthy workers see
  a no-op mkdir; a real ln failure still reports. No flag/test-count
  change; next round acts on the replayed tail instead of re-guessing.

## Preflight 2026-09-27 19:32 (round 25): depfiles is the real killer (this round)

- Comparison (2nd occurrence of this fingerprint since the replay landed,
  strategy differs by construction): round 24 assumed the stdout-only
  death was inside AC_CONFIG_COMMANDS([packageheaders]) (find/sub-make/ln
  loop) and added a DST mkdir plus the `_replay_config_status()` evidence
  channel. The 19:32 preflight ran that tree (exception line moved to 2217,
  `cfgstatus-replay` present) and the replay fired: the tail names
  `config.status: executing depfiles commands` ->
  `config.status: error: Something went wrong bootstrapping makefile
  fragments for automatic dependency tracking ... re-running configure with
  MAKE="gmake" ... or --disable-dependency-tracking`. dof_free_bit.h /
  alberta_util*.h commands all report `is unchanged`; packageheaders was
  never reached. Root cause is therefore the automake depfiles bootstrap
  (dependency-mode probe against the cross toolchain), not packageheaders,
  not mktemp, not RM -- all three prior theories are falsified by this
  single stdout tail.
- Fix (the exact fallback the error message prescribes, no test change):
  `generate()` gains `--disable-dependency-tracking` on the main configure
  (the vendored m4/autoconf/automake builds already carry it in
  `_build_vendor_tool`). Depfiles only govern .deps rebuild tracking; the
  28 upstream TESTS plus the 3 test_package checks are unaffected.
  `manifest.yaml` configure_options synced. Replay + pkgheader hardening
  stay as defense in depth. Effectiveness judged by the next preflight:
  config.status must proceed past `executing depfiles commands`.

## Preflight 2026-09-27 19:49 (round 26): libtool LT_INIT version mismatch (fixed attempt)

- Comparison (new failure domain past configure -- no repeat of depfiles /
  mktemp / RM shadowing): the 19:49 preflight gets past configure
  (round-25 `--disable-dependency-tracking` worked) but `make -j1` dies in
  `alberta_util/src` with `libtool: Version mismatch error. This is
  libtool 2.5.4, but the definition of this LT_INIT comes from an older
  release ... recreate aclocal.m4 with macros from libtool 2.5.4`
  (Error 63 -> all-recursive Error 1/2). The ltmain.sh/libtool script
  (2.5.4, from the Conan libtool tool package deliberately left on PATH)
  disagrees with the LT_INIT macros baked into aclocal.m4 -- upstream
  ships stale libtool .m4 files and autoreconf alone kept them.
- Fix attempt (the exact remedy the error message prescribes, bootstrap
  only, no graph / flag / test-count change): `_bootstrap()` runs the
  matching `libtoolize --force --copy` (PATH-resolved, tool-bindir
  fallback, `--version` logged as evidence) under the same shell-inline
  prefix before the vendored `autoreconf --force --install`.

## Preflight 2026-09-27 20:14 (round 27): purge stale libtool cache, then refresh (this round)

- Comparison (2nd occurrence of the same 2.5.4-vs-older LT_INIT fingerprint
  at the same divers.lo target, strategy must differ -- bare re-run is
  banned): the 20:14 preflight ran WITH the round-26 tree (build() line
  2251 -> 2294 is the round-26 insertion itself) and fails identically, so
  a bare `libtoolize --force --copy` before autoreconf is falsified -- the
  stale generated files (upstream m4/libtool*.m4 + cached aclocal.m4 /
  ltmain.sh) survive it and autoreconf keeps the old macro bodies.
- Fix (purge + refresh + audit, bootstrap only, no graph / flag / test
  change): (1) surgically delete only the libtool-generated cache (top
  aclocal.m4/ltmain.sh + m4/libtool.m4, ltoptions.m4, ltsugar.m4,
  ltversion.m4, lt~obsolete.m4; alberta's own m4 macros preserved) with
  per-file logging; (2) re-run matching libtoolize with --install added;
  (3) after autoreconf audit the LT version line actually baked into
  aclocal.m4 against the libtoolize version. Effectiveness judged by the
  next preflight: `make` must pass divers.lo, or the audit line names the
  stale side.

## Preflight 2026-09-27 19:49 (round 26): libtool LT_INIT version mismatch (this round)

- Comparison (new failure domain past configure -- no repeat of depfiles /
  mktemp / RM shadowing): the 19:49 preflight gets past configure
  (round-25 `--disable-dependency-tracking` worked) but `make -j1` dies in
  `alberta_util/src` with `libtool: Version mismatch error. This is
  libtool 2.5.4, but the definition of this LT_INIT comes from an older
  release ... recreate aclocal.m4 with macros from libtool 2.5.4`
  (Error 63 -> all-recursive Error 1/2). The ltmain.sh/libtool script
  (2.5.4, from the Conan libtool tool package deliberately left on PATH)
  disagrees with the LT_INIT macros baked into aclocal.m4 -- upstream
  ships stale libtool .m4 files and autoreconf alone kept them.
- Fix (the exact remedy the error message prescribes, bootstrap only, no
  graph / flag / test-count change): `_bootstrap()` now runs the matching
  `libtoolize --force --copy` (PATH-resolved, tool-bindir fallback,
  `--version` logged as evidence) under the same shell-inline prefix
  before the vendored `autoreconf --force --install`, so ltmain.sh + m4
  macros + aclocal.m4 all come from 2.5.4. A libtoolize failure only logs
  and autoreconf still runs. Effectiveness judged by the next preflight:
  `make` must proceed past `libalberta_utilities_la-divers.lo`.

## Preflight 2026-09-27 20:30 (round 28): preseed hanging pthread probes (this round)

- Comparison (new fingerprint at an earlier phase -- transport drop, not a
  configure Error 1 or make mismatch, so no repeat of depfiles / libtoolize
  / purge-refresh): the 20:30 preflight drops with
  `Connection to 47.242.172.160 closed by remote host` right after
  `checking for pthread_t...`, zero upstream markers, after a tail of
  malloc-ptrdiff / lstat / select / realpath checks. Upstream audit proves
  these are NOT alberta checks: alberta configure.ac (Debian orig tarball,
  864 files, fetched via aliyun mirror after tuna 403) contains none of
  pthread_t/lstat/select/realpath/french-locale -- they are the vendored
  m4 1.4.19 gnulib suite. The very next test there is
  gl_PTHREAD_RWLOCK_RDLOCK_PREFER_WRITER, a threaded AC_RUN_IFELSE
  (reader/writer/timer relay with usleep) that must not execute on this
  worker; its hang with no output fits the idle-SSH drop exactly.
- Fix (new family -- autoconf cache preseed, no env shadowing / script
  rewrite / flag change): `ac_cv_type_pthread_t=yes` (factual on musl and
  glibc) + `gl_cv_pthread_rwlock_rdlock_prefer_writer="guessing no"`
  (the macro's own musl cross guess) wired at all four layers --
  _inline_prefix (every vendor configure), generate() toolchain env,
  build-scope save_script `alberta_configure_cache` (winning layer for the
  helper command), build() os.environ (defense in depth). Pure
  check-skipping; 28 upstream TESTS + 3 test_package checks unchanged.
  If the next drop moves to a later check, preseed that one instead of
  widening blindly.

## Preflight 2026-09-27 20:56 (round 29): libtool edge retarget to repo-owned 2.5.4.1 (this round)

- Comparison (3rd occurrence of the same 2.5.4-vs-older LT_INIT mismatch at
  alberta_util/src divers.lo, Error 63; strategy must differ -- round 26 bare
  libtoolize and round 27 purge + refresh with the same binary both ran and
  failed identically at 19:49 / 20:14 / 20:56, so re-running either is banned).
- Root cause of the repeat: the libtool edge is the only CCI leg in an
  otherwise-ohpcd toolchain. This repo carries libtool 2.5.4.1 (not 2.5.4),
  so bare `tool_requires("libtool/2.5.4")` resolves conancenter-first and its
  foreign packaging never converges with the vendored aclocal macros, no
  matter how many times the purge + refresh runs.
- Fix (new family -- toolchain version, not refresh mechanics): `build_requirements`
  retargets to repo-owned `libtool/2.5.4.1` (ohpcd binary with the
  _lt_pkgdatadir relocatable fix); `_bootstrap` prefers $LIBTOOLIZE, falls back
  to 2.5.4.1 then 2.5.4 tool bindirs, and forwards _lt_pkgdatadir inline so both
  the explicit libtoolize refresh and autoreconf's internal libtoolize find their
  data files. The round-27 purge is kept; only the binary version and invocation
  change. No flag / test-count change. Effectiveness judged by the next preflight:
  `make` must proceed past divers.lo with a single 2.5.4.1 macro audit line.

## Preflight 2026-09-27 21:22 (round 30): deterministic libtoolize + forced aclocal consistency (this round)

- Comparison (4th occurrence of the LT_INIT mismatch at divers.lo; must differ
  from round 29's edge retarget): the 21:22 preflight ran the round-29 tree
  (graph proves libtool/2.5.4.1 resolved) yet the error still says "This is
  libtool 2.5.4". Falsified: the retarget alone never changed the effective
  binary -- resolution preferred shutil.which() before the tool bindirs and
  broke out of the version loop on any hit, so a system 2.5.4 libtoolize
  shadowed the 2.5.4.1 tool package for both the explicit refresh and
  autoreconf's internal libtoolize.
- Fix (new mechanism -- invocation determinism + search-order, not version):
  (1) tool bindirs (2.5.4.1 first) win over LIBTOOLIZE env and PATH-which
  (last resort, logged with source); (2) after autoreconf, a forced
  consistency pass re-runs the SAME pinned libtoolize --force --copy, then
  vendored aclocal --force -I m4 with --system-aclocal-dir pointed at an
  empty dir (stale system libtool.m4 excluded, Conan pkg.m4 still via
  ACLOCAL_PATH), then vendored autoconf --force -- the error message's own
  prescription with one binary; (3) make failure now raises both-sides
  forensics (build libtool script vs src ltmain.sh vs aclocal.m4 macro vs
  tool-bindir libtoolize versions) in the exception text. No flag/test change.

## Preflight 2026-09-27 21:38 (round 31): single autoreconf with pinned LIBTOOLIZE + cache purge (this round)

- Comparison (new fingerprint, strategy must differ from round 30's
  fragmentary post-pass): the 21:38 preflight no longer reaches make --
  configure dies early with `cannot find required auxiliary files: compile
  missing` (forensics: config.status=no, makefiles=10, config.h=no). The
  round-30 manual libtoolize-copy + aclocal + autoconf re-run rebuilt
  configure WITHOUT automake --add-missing, breaking aux-file consistency
  that autoreconf --install had owned. Repeating fragments is banned.
- Different route (single owner for the whole sequence): (1) delete the
  round-30 fragment block; one full vendored `autoreconf --force --install`
  again owns libtoolize+aclocal+autoconf+automake (incl. --add-missing);
  (2) keep round-30 determinism but enforce single-binary use by exporting
  LIBTOOLIZE=<pinned 2.5.4.1> + leading its bindir in PATH before that
  autoreconf, so its internal libtoolize is provably the same binary as the
  explicit refresh; (3) extend the purge to autom4te.cache (stale macro
  expansions explain the identical LT_INIT mismatch surviving fresh
  aclocal.m4 across rounds 26-30); (4) aux-file presence audit for the next
  round. No flag/test-count change.

## Preflight 2026-09-27 21:55 (round 32): seed libtool files directly, stop trusting libtoolize discovery (this round)

- Comparison (2nd strategy cycle: rounds 29-31 share one root assumption --
  wrong effective libtoolize binary / stale cache -- and re-ran binary
  re-selection + same-file purge three times at 20:56 / 21:22 / 21:38. The
  21:55 preflight falsifies it: `src-ltmain=VERSION=2.5.4` (the refresh DOES
  reach the tree) yet `aclocal-m4=no-LT-version-line` (the aclocal expansion
  never sees the 2.5.4 macro dir). So autoreconf keeps expanding a stale
  LT_INIT while ltmain.sh is new; no further binary re-selection can fix an
  aclocal search-path gap. Repeating selection/purge is banned.
- Probable mechanism: libtoolize locates its m4 files through the repo
  libtool recipe's `_lt_pkgdatadir` shim (relative symlinks under
  `share/libtool-conan`), which can resolve to nothing on this worker while
  the command still exits 0 after updating ltmain.sh -- exactly the split
  the forensics shows.
- Fix (different route -- direct provisioning, not discovery): `_bootstrap`
  now copies the five libtool .m4 files from the pinned package's REAL
  `share/aclocal` dir (symlink-resolved fallback to the shim) into the
  source `m4/` dir plus `ltmain.sh` from `share/libtool/build-aux` (same
  bytes `libtoolize --copy` would install, minus the broken discovery),
  all existence-gated with per-file logging, before the single autoreconf
  owns the sequence; the post-autoreconf audit now reports MATCH/UNMATCHED
  against the seeded version instead of an unanchored grep. No graph, flag,
  or test-count change. Effectiveness judged by the next preflight: the
  audit must read MATCH-2.5.4 and `make` must proceed past divers.lo.

## Preflight 2026-09-27 22:17 (round 33): GNU-tarball file seed + seeded m4/ leads ACLOCAL_PATH (this round)

- Comparison (same fingerprint, 2nd consecutive identical forensics --
  strategy must differ from round 32's package-dir seed): the 22:17
  preflight ran the round-32 tree (build() line 2492 -> 2621 is the
  round-32 insertion itself, so the new code provably executed) yet the
  forensics is byte-identical (`src-ltmain=VERSION=2.5.4`,
  `aclocal-m4=no-LT-version-line`). A seed that ran but changed nothing
  means its source supplied no usable macros on this worker -- the Conan
  tool package's `share/aclocal` + shim path is exhausted as a strategy.
  Re-sourcing from the package (or re-selecting binaries) is banned.
- Fix (different source + unmissable placement, bootstrap only): (1) new
  `_VENDOR_LIBTOOL_FILES` spec fetches the official GNU libtool-2.5.4
  tarball (URL order + sha256 identical to this repo's own
  `archives/l/libtool/2.5.4.1/conandata.yml`, fetch-only, never built --
  same vendoring pattern as m4/autoconf/automake) and seeds the five .m4
  files + `ltmain.sh` from the verified tarball members; (2) the seeded
  source `m4/` dir is prepended to ACLOCAL_PATH on both the os.environ and
  inline-prefix layers ahead of every other entry, so the seeded 2.5.4
  macros shadow any stale ones regardless of whether configure.ac declares
  `m4/`, and `ar_prefix` is rebuilt before the single autoreconf owns the
  sequence. No graph, flag, or test-count change. Effectiveness judged by
  the next preflight: seed log must list 5 copied files, audit must read
  MATCH-2.5.4, `make` must proceed past divers.lo.

## Preflight 2026-09-27 22:38 (round 34): fix the meter, argv -I, configure proof with fail-fast (this round)

- Comparison (same fingerprint, 3rd consecutive identical forensics --
  must differ from rounds 32/33 file-seeding): this round first audited
  the actual sources locally (both tarballs sha-verified in memory).
  Upstream `alberta_3.1.1.orig.tar.bz2` (864 members, SHA matches
  conandata) ships NO libtool .m4 files (m4/ holds 17 own macros only),
  NO ltmain.sh, NO aclocal.m4, NO configure; configure.ac has bare
  `LT_INIT` + singular `AC_CONFIG_MACRO_DIR([m4])`. And GNU
  libtool-2.5.4 (SHA matches this repo's libtool conandata) spells the
  version `LT_PACKAGE_VERSION` (no underscore): the recipe's
  `"_LT_PACKAGE_VERSION|LT_VERSION"` grep can never match 2.5.4 output
  (`LT_VERSION` is not a substring of `LT_PACKAGE_VERSION`), so all
  "no-LT-version-line" verdicts were void meter readings. The fired
  ltmain branch is the EMPTY-macro_version one
  (ltmain.sh `func_check_version_match`: `test -z $macro_version`).
- Fix (different route -- argv channel + proof, not another env seed):
  (1) both greps (macro audit, mismatch forensics) now match both
  spellings; (2) the seeded `m4/` dir is passed as `-I` on the
  autoreconf command line (forwarded to aclocal/autoconf/automake,
  searched before every env/system dir) instead of env-only feeding;
  (3) after autoreconf, the GENERATED `configure` must contain the
  verbatim `macro_version='<ver>'` assignment from the seeded
  ltversion, else bootstrap raises immediately with the artifact dump
  instead of walking into a doomed make; (4) the GNU tarball fetch now
  runs outside the swallowing try so a missing/unverifiable archive
  fails loudly. No graph, flag, or test-count change.

## Preflight 2026-09-27 23:07 (round 35): vendor libtool, single writer single version (this round)

- Comparison (3rd strategy cycle: rounds 32-34 re-ran the same
  seed-then-autoreconf assumption with three seed sources, yet the 23:07
  preflight fails with the identical LT_INIT mismatch at divers.lo.
  Seeding is falsified as a family: the tree has TWO writers with TWO
  releases -- the explicit refresh (Conan 2.5.4.1 binary) runs before the
  seed, the GNU seed (2.5.4 files) overwrites it, then autoreconf's
  INTERNAL libtoolize (pinned to Conan 2.5.4.1 via LIBTOOLIZE) rewrites
  ltmain.sh back mid-run. No seed source can converge that. Repeating any
  seed/pin/-I variant is banned.
- Fix (different route -- build, not copy): `_VENDOR_LIBTOOL_FILES`
  becomes a real vendored build (same fetch-build pattern as
  m4/autoconf/automake), so `bin/libtoolize`, `share/aclocal/*.m4` and
  `share/libtool/build-aux/ltmain.sh` are one release (2.5.4) from one
  source. `_bootstrap` pins LIBTOOLIZE to the vendored binary (explicit
  refresh and autoreconf-internal libtoolize are now provably the same
  file), leads ACLOCAL_PATH with the vendor `share/aclocal`, drops the
  foreign `_lt_pkgdatadir` shim on both layers, and deletes both the
  Conan-bindir refresh block and the GNU-tarball seed block. The purge
  of stale upstream cache, `-I m4` argv, and the generated-configure
  `macro_version` fail-fast proof stay. No graph, flag, or test-count
  change. Effectiveness judged by the next preflight: the vendor
  `libtoolize --version` must read 2.5.4, the configure proof must pass,
  and `make` must proceed past divers.lo.

## Preflight 2026-09-27 23:38 (round 36): gates + guaranteed re-expansion + forensics fix (this round)

- Comparison (4th strategy cycle: rounds 32-35 assumed the stale side was
  at or before aclocal.m4 and re-seeded/re-built the macro supply three
  times plus a vendor build. The 23:38 preflight ran the round-35 tree
  (build() line 2764 -> 2664) yet fails identically, and its forensics
  carries two falsifications: (a) aclocal.m4 NOW has the fresh 2.5.4 LT
  line, so the macro supply converged -- the stale side must be
  DOWNSTREAM (configure expansion or libtool script substitution);
  (b) make executed `../../libtool` yet forensics said
  build-libtool=absent, so the single hard-coded probe path is wrong
  (build_folder already ends in build-release) or stat hits an HMFS
  quirk. Also the Conan libtoolize reports GNU libtool 2.5.4 anyway, so
  both sides were always 2.5.4 -- the dual-version theory is dead.
- Fix (different route -- gates + re-expansion, no toolchain/seed
  change): (1) fail-fast gate on FINAL aclocal.m4 freshness right after
  autoreconf (missing LT 2.5.4 line raises immediately); (2) explicit
  vendored `autoconf --force` re-run so configure is provably expanded
  from the final aclocal.m4 (autoconf-only: rewrites just configure,
  aux files untouched, unlike the round-30 fragment); (3) strict
  configure proof -- empty expectation now raises instead of entering a
  doomed make; (4) forensics rewritten to multi-location libtool probing
  with stat/read distinction plus the generated-configure
  macro_version/macro_revision dump. The HMBS `[readonly_tmp]` note is
  already covered (every bootstrap/vendor command carries inline
  TMPDIR/TMP/TEMP; no Read-only-FS line in the visible log). No graph,
  flag, or test-count change. Effectiveness judged by the next
  preflight: either `make` passes divers.lo, or the corrected forensics
  names the true stale side.

## Preflight 2026-09-28 00:03 (round 37): repair the built libtool script (this round)

- Comparison (5th strategy cycle: rounds 32-36 all fought over the macro
  supply, yet the 00:03 preflight ran the round-36 tree (build() line
  2664 -> 2730, new forensics present) and fails identically. The
  round-36 forensics itself falsifies the whole family: configure holds
  `macro_version='2.5.4'`, but the BUILD script is byte-size-identical
  to ltmain.sh (337554 == 337554). Local audit of the sha-verified GNU
  libtool-2.5.4 sources (mirrors.aliyun, sha matches this repo's libtool
  conandata) proves the generated script must be header + full ltmain:
  `_LT_CONFIG` writes the `### BEGIN LIBTOOL CONFIG` header with the
  macro assignments, then appends the whole ltmain (`$SED '$q'` prints
  all lines), then moves it over ofile; `func_check_version_match`
  reads `$macro_version`, which only the header provides
  (`generated_by_libtool_version='$macro_version'` is the only other
  reference). A byte-equal file is therefore a verbatim ltmain copy
  whose header never landed -- `$macro_version` is empty at runtime
  (the exact "older release" branch), and the file is written
  downstream of every aclocal/autoconf step, so no macro-supply change
  can fix it. Upstream audit (Debian tarball, sha matches conandata):
  bare `LT_INIT`, no `LT_OUTPUT`, `BUILT_SOURCES = libtool` (standard
  automake `libtool: $(LIBTOOL_DEPS)` rule), `AC_CONFIG_LINKS` covers
  only test data -- no upstream custom copy rule, so the repair below
  is worker-side only and upstream-clean.
- Fix (different route -- repair at the exact broken step, no
  toolchain/seed/macro change): new `_ensure_built_libtool()` runs
  between configure and make -- verifies the header marker in the
  build-root script (no-op probe when correct), otherwise deletes the
  bogus file and re-runs the canonical `./config.status libtool`
  (the same command make's own rule uses) with pinned
  CONFIG_SHELL/SHELL, then fail-fasts with the captured log unless
  marker + `macro_version` are present. Forensics extended in parallel:
  full-file (not 12KB-window) macro grep, first-line dump, symlink
  detection, and the top-Makefile `libtool:` rule + `LIBTOOL_DEPS`
  dump. `[readonly_tmp]` needs no new handling (all commands already
  carry inline TMPDIR/TMP/TEMP; no Read-only-FS line in the log). No
  graph, flag, or test-count change. Effectiveness judged by the next
  preflight: `make` must pass divers.lo, or the fail-fast names the
  broken sub-step inside `./config.status libtool`.

## Preflight 2026-09-28 (round 38): readonly /tmp kills one 1d demo + early abort hides total (this round)

- Comparison (new phase, not the libtool family): rounds 32-37 fought the
  LT_INIT macro supply (seed/package/vendor/gates/re-expansion/repair) and
  the 00:55 preflight proves that fight is OVER -- configure passes and
  `make -j1` completes; the death moved downstream to `make check` in
  `alberta/tests/book-demo/1d` (# FAIL: 1, discovered 3 / executed 3 /
  passed 2 / failed 1). Re-running any libtool refresh is therefore banned
  by the strategy-cycle rule; the failing step was never touched before.
- Root cause (two parts, both evidenced): (1) HMBS platform diagnosis
  `[readonly_tmp]` fires, and the local source audit (Debian
  alberta_3.1.1.orig.tar.bz2, 864 members, sha matches conandata) finds the
  only /tmp writer on the 1d test path in
  `alberta_util/src/parameters.c:init_parameters_cpp()` -- `sys_test(
  "test -w", "/tmp")` then `sprintf(tmp_file, "/tmp/%s.cpp", ...)` plus the
  cpp preprocess + fopen + ERROR_EXIT chain every 1d demo (ellipt1d/heat1d/
  ellipt-periodic1d) runs through its INIT/*.dat parameter file. On the
  worker /tmp is read-only, so the branch is skipped; worse, `tmp_file` is
  never initialized, so the `*tmp_file == 0` fallback test reads stack
  garbage -- flaky by construction (2 pass, 1 fails). Graphics-path
  `/tmp/blah` writers are out of scope (--disable-graphics). (2) The
  marker reports discovered=3 of the 28 registered TESTS because plain
  `make check` stops at the first failing suite (check-recursive aborts at
  book-demo/1d); later suites never produce test-suite.log, so the count
  is an executed-subset, not the official total the manifest declares.
- Fix (minimal adaptation, no test removed): (1) new conandata patch
  `patches/0001-tmpdir-aware-cpp-tempfile.patch` -- initializes
  `tmp_file[0]`, resolves the temp root from TMPDIR/TMP/TEMP (first
  writable wins, HMBS-injected), keeps /tmp only when actually writable,
  falls through to the existing alongside-fn branch otherwise; adds the
  missing `<stdlib.h>` for getenv. Verified by extracting the sha-pinned
  tarball and `git apply --check/apply` (clean). (2) `build()` runs
  `make -k check` instead of `make check` -- same tests, keep-going so all
  suites emit test-suite.log and the marker aggregates the true total;
  `make -k` still exits non-zero on any failure. Marker/manifest command
  strings updated to `make -k check` so the evidence names the real
  command. No flag/graph change; XFAIL counted as passed per automake.
  Effectiveness judged by the next preflight: 1d must pass via TMPDIR and
  discovered must equal the registered total.

## Preflight 2026-09-28 (round 39): out-of-source build misses INIT/Macro test data (this round)

- Comparison (new phase, not libtool/tmpdir/-k): round 38 fixed the 1d cpp
  tempfile (/tmp -> TMPDIR) and switched to `make -k check`; the 03:17
  preflight proves both landed (command is `make -k check`, discovered 25)
  yet 8 of the 10 non-XFAIL suites fail while all 15 XFAIL pass as expected
  (passed 17 = 15 XFAIL + 2 real). Re-running libtool refresh, tmp shadowing,
  or flag changes is banned; the failing step (test data resolution) was never
  touched before.
- Root cause (source-audited, sha-verified Debian tarball, 864 members): every
  book-demo binary runs `parse_parameters(..., "INIT/xxx.dat")` and each .dat
  references `Macro/*.amc` via a bare relative path; no book-demo Makefile.am
  provisions INIT/Macro into the build dir (only libalbas/tests has an all-local
  LN_S). Upstream CI builds in-source where the paths resolve; Conan builds
  out-of-source (build_folder=.../build-release mirrors the source tree), so
  ./INIT and ./Macro are absent where the tests execute and every suite dies
  opening its parameter/macro file -- the systematic all-suite signature.
  Discovered 25 (not 28) is upstream's own HAVE_LIBLTDL gate (2d stokes trio
  unbuilt without -lltdl), already documented in MANIFEST.yml, not a skip.
- Fix (minimal, no test removed, no flag/graph change): new
  `_provision_test_data()` runs after `make -j1` and before `make -k check`,
  symlinking each source INIT/Macro dir into the matching build subdir under
  alberta/tests + add_ons test roots (HMBS symlink=1; copy fallback;
  idempotent; in-source no-op). Effectiveness judged by the next preflight:
  the 8 non-XFAIL suites must pass with INIT/Macro resolved.

## Preflight 2026-09-28 (round 40): writable copies into all roots + FAIL evidence channel (this round)

- Comparison (2nd occurrence of the 25/17/8 fingerprint; strategy must differ
  from round-39 silent symlinks): the 04:06 preflight ran the round-39 tree
  (build() line 2774 matches the patched tree) and fails byte-identically, so
  silent symlinks into one root are falsified -- either they landed in the
  wrong root, were unwritable (writes redirect into the read-only source
  cache), or the cause is elsewhere entirely, and the summary preserves no
  per-suite names to tell which. Repeating symlinks is banned.
- Source evidence against graphics/tmp theories (same tarball, sha matches):
  geomview `popen("tee /tmp/blah...")` sits inside `#if DEBUG_TOGEOMVIEW` (0,
  dead code); the live path uses pipe/fork/execlp(geomview) only reachable via
  togeomview(), which is stubbed with --disable-graphics; `write_macro(...,
  "Macro/blah.amc")` exists only in ellipt-torus (XFAIL) and 5d (not built).
  The remaining systematic suspect is still file resolution, but now at the
  writability/layout layer rather than existence.
- Fix (different mechanism): (1) `_provision_test_data` now installs writable
  COPIES first (copytree) with symlink only as fallback, verifies/replaces a
  pre-existing symlink dir that fails a write probe, and provisions into every
  candidate build root (build_folder plus nested build-release when distinct),
  returning a `testdata[src/copied/linked/skipped]` verdict; (2) new
  `_test_failure_details` parses every build-tree test-suite.log for per-file
  TOTAL/PASS/XFAIL/FAIL plus FAIL:/XPASS:/ERROR: names; (3) build() embeds
  make error + verdict + failsuite in the raised exception (rounds 22-24
  pattern), keeping the upstream marker emission on both paths. No flag,
  test-count, or macro-supply change. Effectiveness judged by the next
  preflight: either green, or the exception names the exact failing suites.

## Preflight 2026-09-28 (round 41): per-test log tails + tmp writability probe (this round)

- Comparison (3rd occurrence of the 25/17/8 fingerprint; must differ from
  round-39 symlinks and round-40 copies): the 04:56 preflight ran the round-40
  tree (`testdata[src=18 copied=6 linked=0 skipped=12]` in the exception) and
  the new failsuite channel names the exact set: 1d FAIL heat1d; 2d FAIL
  ellipt2d/heat2d/ellipt-dg2d; 3d FAIL
  ellipt-periodic3d/stokes3d/quasi-stokes3d/quasi-stokes-slip3d -- while
  ellipt1d and ellipt-periodic1d PASS in the same directories with the same
  provisioned data. File-missing is therefore falsified as the cause of these
  8: identical data resolution, selective runtime aborts (exit nonzero).
- Source audit for a discriminating mechanism (same sha-verified tarball):
  no .dat carries cpp directives (all share one parameter path); graphics
  /tmp writers are dead code or disabled stubs; heat.c statistics fopens are
  NULL-guarded; the pattern is scale-dependent (tiny 1d ellipt passes, larger
  2d/3d and transient heat fail), pointing at per-test abort lines that live
  only in each <testname>.log, never in the suite summary.
- Fix (new evidence layer, no flag/test-count change): (1) new
  `_fail_test_log_tails` appends each failing test's own .log tail,
  preferring error/abort/solver/diverg/cannot/segfault/assert lines, capped
  into the raised exception; (2) new `_tmp_probe_verdict` measures
  TMPDIR/TMP/TEMP plus /tmp with real file-write probes at check time and
  appends `tmpprobe[...]` to the verdict, settling the every-round
  [readonly_tmp] flag with a number. Effectiveness judged by the next
  preflight: the exception must carry the exact abort lines (solver message,
  missing-file ERROR, or signal note) for a precise round-42 fix.

## Preflight 2026-09-28 (round 42): optimizer hardening + writer-side output dirs (this round)

- Comparison (5th strategy cycle: rounds 39-41 share one root assumption --
  tests fail for lack of INIT/Macro files -- and re-ran it three times
  (silent symlinks -> writable copies into all roots -> per-test tails plus
  tmp probes) with byte-identical 25/17/8 forensics. File-missing is
  falsified twice over: (a) ellipt1d and ellipt-periodic1d PASS in the same
  directories with the same provisioned data while heat1d segfaults there;
  (b) upstream CI itself builds out-of-source (configure in
  build/out/of/source, Debian/Ubuntu jobs) with no INIT provisioning step,
  yet is green -- fopen absence is silent (read_parameters returns, params
  stay default) and cannot abort. Repeating any provision variant is banned.
- New evidence from the round-41 tails (first time the exact abort lines
  survived): heat1d SIGSEGV (139) after solver output; ellipt2d/ellipt-dg2d/
  ellipt-periodic3d SIGABRT (134) in free_dof_index ("Double free of DOF
  index", dof_admin.c); heat2d adapt.c:691 line is benign INFO (missing-param
  notice, returns 0) while the fatal is the same dof abort; stokes3d
  "Cannot open file './data_stokes/...' for writing" (no data_stokes dir
  exists in the 864-member tarball, no mkdir in any test source or
  Makefile.am -- fresh-tree writer bug, not a reader-data bug).
- Fix (two different mechanisms, neither is reader-data provisioning):
  (1) OHOS-only optimizer hardening -- append -fno-strict-aliasing plus a
  winning -O1 after the profile -O3 at all three env layers (toolchain
  extra_cflags/cxxflags + conanbuild env, build-scope save_script, live
  os.environ), gated on settings.os == OHOS so Linux CI keeps -O3; targets
  the heap-corruption family (double-free/SIGSEGV/SIGABRT) in this legacy
  pointer-cast-heavy FEM code on clang/aarch64/musl. (2) New conandata patch
  0002-ensure-output-dirs.patch -- generate_filename() (divers.c, the
  central choke point for stokes/quasi-stokes/heat writers) mkdirs the
  directory part best-effort; covers data/ and data_stokes/ on fresh trees.
  Provisioning kept as-is (inputs correct, not reverted). No test skipped,
  no assertion removed, no TESTS count change.
- Effectiveness judged by the next preflight: the 6 solver crashes must move
  (pass or change signature) under -O1/-fno-strict-aliasing, and the stokes
  write errors must disappear via the mkdir patch.

## Preflight 2026-09-28 (round 43): stop failing the package on upstream TESTS failures (this round)

- Same 25/17/8 fingerprint WITH the round-42 tree (compile lines carry
  -fno-strict-aliasing -O1, testdata copied, TMPDIR writable, all 15 XFAIL
  pass, 8 solver suites abort with SIGSEGV/SIGABRT + free_dof_index +
  adapt.c abort lines while solver output is present). Optimizer and
  file-layout routes are falsified; no further flag/data change this round.
- Fix is verdict plumbing only: build() no longer raises on `make -k check`
  failure but records per-suite test_failure gaps in the marker (counts from
  the same test-suite.log parse, sum equals failed) and continues to
  package(); only a missing test-suite.log still raises as incomplete. No
  test skipped, no assertion removed.

## Preflight 2026-09-28 (round 44): reconcile gaps with official total 28 (this round)

- Comparison (same 25/17/8 fingerprint WITH the round-43 tree; strategy differs: no solver/flag/data change): rule4 rejects because gaps sum to 8 (failed) while actual gap is 11 (official 28 - passed 17). The 3 delta is upstream's own HAVE_LIBLTDL conditional in alberta/tests/book-demo/2d/Makefile.am (stokes2d/quasi-stokes2d/quasi-stokes-slip2d), verified by local audit of the sha-pinned Debian tarball (864 members): with --disable-debug and 4d/5d off, official TESTS = 3 read_mesh + 3 book-1d + 9 book-2d (6 base + 3 ltdl trio) + 9 book-3d + 4 libalbas = 28; without -lltdl the worker registers 25, already documented in MANIFEST.yml but never carried in gaps.
- Fix (verdict plumbing only, counts untouched): _emit_upstream_test_result keeps discovered/executed/passed/failed/skipped purely from test-suite.log (# TOTAL/# PASS/# XFAIL/# SKIP/# FAIL+XPASS+ERROR single source) and appends one environment gap (count = 28 - discovered) with three probed evidences -- source Makefile.am gate lines, generated 2d Makefile TESTS line, config.log ltdl probe -- plus status=failed/reason when unregistered > 0. Sum(gaps) now equals 28 - passed (8 test_failure + 3 environment = 11). No test skipped, no assertion removed, no flag/graph change.
