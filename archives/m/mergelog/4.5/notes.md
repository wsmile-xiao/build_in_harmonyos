# mergelog 4.5 adaptation notes

## Scope

- Target package: `mergelog/4.5`
- Branch: `feat/mergelog-4.5`
- Upstream author: Bertrand Demiddelaer <bert@b3rt.org>
- Upstream series: 4.5 (SourceForge release directory `mergelog/4.5`)

## Upstream verification

### Source URL & release identification

- Official project: `https://mergelog.sourceforge.net/` (homepage recorded in
  the Debian `copyright` and OpenMandriva `mergelog.spec` `URL:` field).
- Official release tarball: `mergelog-4.5.1.tar.gz` on SourceForge, in the
  `mergelog/4.5/` release directory (SourceForge RSS confirms the 4.5 series
  directory exists). The actual `VERSION=` in `configure.in` and the ChangeLog
  entry `release 4.5.1` show the final upstream release in the 4.5 series is
  **4.5.1**; the SourceForge directory label `4.5` is the series name.
- The recipe version is therefore `4.5` (the series the task targets) and the
  conandata `sources` point at the 4.5.1 tarball — the only upstream release
  tarball for that series.

### Source reachability / mirror choice

- Direct SourceForge downloads are currently blocked by Cloudflare 403 for
  non-interactive clients (verified against `downloads.sourceforge.net` and
  several `*.dl.sourceforge.net` mirrors — all redirect to the 403 front).
- The Debian pool carries the upstream pristine-tar copy as
  `mergelog_4.5.1.orig.tar.gz`, covered by a PGP-signed `.dsc` manifest whose
  `Checksums-Sha256` line pins the exact SHA-256 we use in conandata. The bytes
  are thus provably upstream-identical, and `deb.debian.org` is a stable,
  canonical mirror (the same mirror the existing `a52dec` recipe uses).
- conandata URL: `https://deb.debian.org/debian/pool/main/m/mergelog/mergelog_4.5.1.orig.tar.gz`
- SHA-256: `3fd6c8cddbcb1d6500010168aa812a157147851bcdcf9599a25dca0317749da1`
- (R39: official source. Debian pool is an authoritative distro mirror of the
  upstream tarball, not a personal fork / unknown CDN.)

### License

- `COPYING` is the full GPLv2 text.
- `src/mergelog.c` header: "version 2 of the License".
- → `license = "GPL-2.0-only"` (no "or-later" wording present).

## Upstream test audit (evidence)

The release tarball contains **no formal test suite**:

- Full file listing of the extracted `mergelog-4.5.1/`:
  `AUTHORS COPYING ChangeLog INSTALL Makefile.am Makefile.in NEWS README
  aclocal.m4 configure configure.in install-sh missing mkinstalldirs
  src/{Makefile.am,Makefile.in,mergelog.c} man/{Makefile.am,Makefile.in,
  mergelog.1,zmergelog.1}` — no `tests/`, no `test/`, no `check/` directory.
- `Makefile.in` (root and `src/`): the only `check` target is the automake
  default `check: check-recursive` / `check-am: all-am`, i.e. a no-op that
  only ensures binaries build. There is no `TESTS` variable and no test
  script is invoked.
- `configure.in` / `configure`: no `AC_CHECK_TEST`, no test harness setup;
  `configure`'s `test` occurrences are shell conditionals, not test programs.
- No CI scripts: 2001-era project, predates CI; the SourceForge project has
  no `.github/` or appveyor config.
- Conclusion: upstream = **0 tests, 0 assertions**. Recorded in
  `test_package/MANIFEST.yml`.

Because there is no upstream test suite to run, the OHOS toolchain does not
need to execute `make check` for real; the consumer `test_package/` provides
the functional verification instead (see below).

## Toolchain verification (real OHOS, not host)

Confirmed on the build host (HarmonyOS aarch64):

- `clang --version` → `clang version 15.0.4`, `Target: aarch64-unknown-linux-ohos`.
- A trivial hello-world compiled with it is `ELF64 LSB arm64`,
  `Machine: AArch64`, interpreter `/lib/ld-musl-aarch64.so.1`, and runs
  natively — i.e. the real OHOS musl toolchain, not a host gcc.
- mergelog's single `.c` builds with that clang to the same ELF64 AArch64
  PIE shape, links `-lz`, and runs: `mergelog` with no args prints usage and
  exits 1; `mergelog a.log b.log` emits the date-sorted merge.

## Build approach

- Autotools (autoconf 2.13 era): tarball ships a pre-generated `configure`
  + `Makefile.in`. Recipe uses Conan `Autotools`/`AutotoolsToolchain`.
- OHOS cross triplet: `aarch64-unknown-linux-ohos` passed to
  `--build`/`--host` so the ancient `configure` doesn't probe a host triplet.
- No `config.guess`/`config.sub` in the tarball, so we don't patch them; the
  explicit `--host` avoids the missing-config-sub path entirely.
- `zlib/1.3.1` is declared as a Conan `requires` (the configure `AC_CHECK_LIB(z)`
  needs it; `system_libs = ["z"]` is declared for the musl dynamic link).

## Patches

Two upstream bug-fix patches (from the Debian package, vendored verbatim):

1. `0001-fix-scan-offset.patch` — SCAN_OFFSET 9→8 (Debian #538859). Without
   it the date substring is parsed one byte too far in and merged ordering is
   wrong. This patch is what makes the test_package ordering assertion pass.
2. `0002-fix-linker-order.patch` — `$(LIBS)` moved after the object file in
   `src/Makefile.am` so `ld.lld` resolves zlib symbols for `mergelog` and
   `zmergelog`. Without it the link fails with modern `--as-needed` linkers.

Both are `patch_type: official_bugfix` (upstream bug fixes, not OHOS-specific
portability shims), sourced from `sources.debian.org`.

## test_package design

Since upstream has no tests, the consumer test fills the gap with real CLI
behavior (R34: test must actually exercise the packaged package, not be
build-only):

- `a.log` / `b.log`: real Common Log Format fixtures with interleaved
  timestamps (55:36, 56:00 vs 55:50, 57:00).
- Assertion 1: `mergelog` with no args prints usage, non-zero exit.
- Assertion 2: `mergelog a.log b.log` → 4 lines in ascending date order.
- Assertion 3: `zmergelog a.log b.log` (plain inputs via the gzip-aware
  binary) → identical to mergelog output.
- Assertion 4: `zmergelog a.log.gz b.log.gz` (real gzip streams, via zlib) →
  identical to mergelog output. This proves the zlib dependency path
  end-to-end on OHOS.

## Decisions / deviations

- Recipe version `4.5` (the series the task targets); conandata fetches the
  `4.5.1` tarball because that is the only and final upstream release in the
  4.5 series. Documented in README.md and manifest.yaml.
- No `make check` in `build()` because upstream's `check` is the empty
  automake default (verified above); running it adds zero assertions. The
  real verification is the test_package, which is required by the task and
  run by both `conan create` and `ci/conan/build_and_test.sh`.
