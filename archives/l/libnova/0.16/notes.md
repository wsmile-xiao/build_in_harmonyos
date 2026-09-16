# libnova 0.16 adaptation notes

- Upstream has no downloadable release tarball any more: the SourceForge
  `files` area is gone and only the `v0.16` git tag exists. The source is
  the Debian `libnova_0.16.orig.tar.xz` pristine orig tarball; its tree
  was verified file-by-file identical to the upstream `v0.16` git tag
  (`diff -r` empty) and the SHA256 is pinned in `conandata.yml`.
- The tarball ships no `configure` and no generated autotools files, so
  the recipe is an autoreconf recipe: `tool_requires("automake/1.18")` +
  `tool_requires("libtool/2.5.4")` (both already available in the remote;
  same pattern as `abiword-plugin-clarisworks`). `autoreconf --install`
  installs config.guess/config.sub from the automake/1.18 package, but
  even that script (config.guess 2024-07-27) cannot identify the
  HarmonyOS build host (`uname -s` = "HarmonyOS", kernel "HongMeng
  Kernel"; verified - it exits 1 with "unable to guess system type"), so
  the recipe passes `--build=aarch64-unknown-linux-ohos` /
  `--host=aarch64-unknown-linux-ohos` explicitly; automake/1.18's
  `config.sub` accepts that triplet.
- Patch 1 (`0001-respect-user-cflags.patch`): upstream `configure.ac`
  unconditionally sets `CFLAGS=-Wall` (overriding the conan toolchain
  flags) and `src/Makefile.am` hardcodes `-Wall -O3`. Same cause as
  Gentoo's `libnova-0.16.0-cflags.patch`.
- Patch 2 (`0002-add-tarball-version.patch`): upstream's `AC_INIT` derives
  the version through `git-version-gen`, which reads `.tarball-version`;
  without it the version becomes "UNKNOWN". The patch adds the file so
  the packaged version stays 0.16.
- Upstream ships a `CMakeLists.txt` pinned to `cmake_minimum_required(
  VERSION 2.6)` - too old to use; the Autotools path is canonical.
- No third-party build dependencies; only libm is linked. Upstream
  `src/libnova/Makefile.am` uses `-release 0.16`, so the shared library
  installs as `libnova-0.16.so.0.0.0` with no `libnova.so` dev symlink;
  the recipe creates the symlink in `package()` for normal `-lnova`
  consumers (pkg-config name `libnova`).

## Upstream tests (lntest)

`lntest/Makefile.am` registers `lntest` as `noinst_PROGRAMS` only - there
is no `TESTS` primary anywhere, so automake's `make check` builds the
binary but never runs it. The recipe therefore builds `lntest` explicitly
and runs it during `conan create`, parsing the textual `[PASSED]`/
`[FAILED]` output because the upstream harness returns 0 unconditionally
even on failures.

Result on OHOS aarch64 (340 assertions): 316 PASSED, 24 FAILED. All 24
failures were verified to be platform-independent (identical Expected/
calculated values under the second toolchain build - see evidence 1
below), i.e. NOT HarmonyOS-specific regressions; they are recorded as
failures. Independent evidence that a fixture expectation itself is
wrong exists for only 5 of them (nutation 3, Pollux transform 2 - see
evidence 2 and 3). The remaining 19 (solar 3, comets 9, RST 7) have no
independent recomputation on record; only the platform-independence
check below applies to them.

1. Platform independence: the same 24 assertions fail with *identical*
   Expected/calculated values on a second build of the same sources with
   the OHOS SDK clang 15 / musl sysroot on the same aarch64 OHOS host
   (native toolchain, `-dynamic-linker /lib/ld-musl-aarch64.so.1`) - all
   340 values match bit-for-bit across the two toolchains.
2. Upstream already fixed 3 of them: commit 7b60adc (2016-09-12, after
   the 2015-03-03 v0.16 tag) changed the nutation expectations to
   `-3.788/3600 = -0.00105222`, `9.443/3600 = 0.00262306` and
   `23d26'27.407" = 23.44094639` (Meeus values) - which are exactly the
   values this library computes on OHOS.
3. Independent reduction of the Pollux transform fixture: the SIMBAD J2000
   RA/Dec position (113.215630/6.684170 when transformed with the J2000
   obliquity) is NOT comparable to the library result because the test
   epoch is 1987-04-10 (JD 2446896.30625), not J2000. Reducing the same
   RA/Dec with the epoch-correct Meeus 22.2 mean obliquity
   (eps0 = 23.44094620 deg at that JD) yields lng=113.21555278,
   lat=6.68264899 - bit-identical to the library (8 decimals), while the
   frozen expectation (113.21542105 / 6.68002727) is the outlier: it
   corresponds to an obliquity roughly 0.0056 deg off, i.e. pre-epoch
   rather than epoch-correct. The frozen value dates from upstream
   commit 4337a98 (2013-11-24).
4. The RST algorithm (`rise_set.c`) has not changed since the SVN era:
   commit 4337a98 (2013-11-24) is a pure style cleanup (token-stream
   identical after normalization). This only rules out a local code
   regression; it is NOT independent evidence that the 7 minute-
   granularity RST expectations are correct. They remain recorded as
   failures.
5. The comet (Enckle, Kudo-Fujikawa) differences are 3e-6..5e-4
   AU/degree - consistent with numerical drift of the same iterative
   algorithm, far below astronomical significance, but this is an
   inference, not an independent recomputation; the assertions remain
   recorded as failures, and the 1e-8 assertion tolerance stands.

Fail-closed gate: the recipe parses the harness output and requires
EXACT equality with the known-good signature - exactly 316 PASSED,
exactly 24 FAILED, 340 assertions total (`(passed, failed) != (316, 24)`
raises). Any new failure, any disappearance of a test line, or any
unexpected change in the pass/fail split of the known 24-failure set
(which would mean the sources changed) aborts `conan create`.

## Consumer verification (test_package)

39 checks against reference vectors with algorithm-derived tolerances
(documented inline in `test.c`): exact conversions get 1e-8 deg, Julian
day 1e-9 day, sidereal time 1e-7 h (printed Meeus precision), nutation /
solar / planetary positions 3e-4..1e-5 deg (VSOP87 truncation), lunar
0.01 deg (truncated ELP theory), RST times 1e-3 day (lntest asserts
minute granularity). Both static and shared consumers pass on OHOS
aarch64.

## OHOS-specific package check (test_ohos.sh, 11 checkpoints)

Independent of the consumer test above (counted separately). Driven from
`test_package/conanfile.py::test()` when `settings.os == "OHOS"`:

- C1 tool availability (readelf, llvm-objcopy, binary-sign-tool; ar for
  static packages) - fail closed, no silent skip.
- C2 packaged library present in `lib/`: shared `libnova-0.16.so.0*` or
  static `libnova.a` (mode auto-detected and logged).
- C3 static mode: every ar member is ELF64 / little-endian / AArch64
  REL (an archive has no SONAME/PT_INTERP by definition - not claimed).
- C4 shared mode: library is ELF64 / little-endian / AArch64 DYN.
- C5 shared mode: `DT_SONAME == libnova-0.16.so.0` and the soname file
  exists (libtool `-release 0.16 -version-info 0` rule).
- C6 `DT_NEEDED` of library and consumer exe within the OHOS musl
  allowlist (`libc.so`, `libm.so`, `libnova-0.16.so.0`); no `GLIBC_*`
  versioned symbols.
- C7 no RPATH / RUNPATH.
- C8 no build-machine absolute paths (`/home/`, `/storage/Users/`,
  `.conan2/p/`) embedded in the library, public headers or executable.
- C9 consumer exe is ELF64 / LE / AArch64 with a musl `PT_INTERP`.
- C10 consumer exe carries an OpenHarmony `.codesign` section
  (self-signed with llvm-objcopy + binary-sign-tool, same flow as
  boost/1.91.0).
- C11 the signed exe runs on the device and its astronomy assertions
  pass (ohos_check.c, 3 textbook anchors: JD 2451545.0 at 1e-9 d,
  J2000.0 mean obliquity 23.43929111 deg at 1e-6, GMST 18.697374558 h
  at 1e-6).
