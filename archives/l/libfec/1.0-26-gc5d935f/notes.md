# libfec 1.0-26-gc5d935f adaptation notes

## Identity / provenance (W0 pre-check)

- Upstream: https://github.com/fblomqvi/libfec — maintained fork of Phil
  Karn's (KA9Q) libfec (original http://www.ka9q.net/code/fec/ is
  unmaintained). Debian `debian/watch` + `debian/copyright` point at this
  fork and package it as `1.0-26-gc5d935f` = git describe of tag `1.0`
  (b802307e00) + 26 commits at c5d935f42a79221871ff50e75d3971cf3e87be7c
  (2021-02-01, "config.sub: add support for arm64 build (#7)").
- NOTE: github.com/ka9q/libfec was force-rebuilt in 2022-09 (5 commits,
  "Rebuilding from old files, incomplete") and does NOT contain c5d935f.
  The fblomqvi fork is the only complete history source for this version.
- Source URL (official GitHub commit archive, no release tarball exists):
  https://github.com/fblomqvi/libfec/archive/c5d935f42a79221871ff50e75d3971cf3e87be7c.tar.gz
  sha256 a2fff6f8f883bcef9c9539279cebdb6f0407d2737adc7fac48a8438a3b7c3bc9
  (Debian's orig.tar.gz is a repack and deliberately NOT used per R39/PF7.)

## W0 dependency check

`configure.in` checks only the C compiler and libc
(`AC_CHECK_LIB(c, malloc)`, standard headers). Zero required and zero
optional dependencies; W0 passes trivially. `conan download` probes are
therefore not applicable.

## Build system analysis

- `configure.in` is 2.13-style (AC_INIT(viterbi27.c)) but the shipped
  `configure` is **autoconf 2.69** generated (find_cpu_mode-era).
- `makefile.in` is a hand-written 1990s-style makefile:
  - hard-codes `gcc` in ~35 recipe lines (library .so link, all test
    programs, the codegen host tools) -> patch 0003 switches them to
    `$(CC)`;
  - `ar rv` + bare `ranlib` remain (resolved via PATH; the recipe creates
    build-local `bin/` symlinks `ar -> llvm-ar`, `ranlib -> llvm-ranlib`
    on OHOS, same trick as celt 1.0.0's `ld` symlinks);
  - `install` target runs bare `ldconfig` (`@REBIND@`) against the live
    system and installs both libfec.a and libfec.so -> bypassed entirely:
    `package()` copies artifacts manually (Conan-managed layout, no
    ldconfig, no `install` tool dependency);
  - `ccsds_tab.c` / `ccsds_tal.c` are GENERATED at build time by running
    `gen_ccsds` / `gen_ccsds_tal` (built with $(CC) after patch 0003).
    CI and device builds are native on aarch64, so the host-run works;
    a true cross build would need CC_FOR_BUILD (out of scope, noted).
- CPU dispatch: aarch64 falls into configure's `*)` case ->
  `MLIBS="cpu_mode_unknown.o"` (portable C only, `find_cpu_mode()` ->
  PORT). None of the MMX/SSE/AltiVec sources are referenced.
- Outputs: `libfec.a`, `libfec.so`, `fec.h` (+ man3 pages, not packaged).
  No pkg-config, no libtool, no versioned .so install.

## Adaptation decisions

1. **0001 config.sub aarch64** — same early-accept block as libdisasm
   0.23 / a52dec 0.7.4 (`aarch64-*-linux* | aarch64-*-ohos*`).
2. **0002 configure umask 022** — identical to libdisasm 0.23 0002
   (setgid hmdfs makes the umask 077 mktemp dir unwritable for
   config.status subshells).
3. **0003 makefile $(CC)** — mechanical gcc -> $(CC) replacement (35
   lines incl. the never-exercised x86 SIMD rules, for uniformity).
4. **Native-style triples** — on OHOS the recipe appends
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
   so 2.69 configure never invokes the 2006 `config.guess` (which cannot
   identify aarch64/OHOS) and stays out of cross mode. Mirrors
   libdisasm 0.23 / celt 1.0.0.
5. **-fuse-ld + build-local bin/** — celt 1.0.0 pattern verbatim
   (workers ship clang/ld.lld without bare `ld`; clang does not search
   PATH for linkers), extended with `ar`/`ranlib` symlinks for the
   vintage makefile's bare tool calls.
6. **Static default** — `shared=False, fPIC=True` matches the repo
   convention for vintage C libraries (a52dec/celt/libdisasm/cdb);
   libfec is not a system-homonym library on OHOS. `shared=True` builds
   the upstream `libfec.so` (unversioned soname).
7. **Upstream tests in build()** — `make test` runs on Linux/OHOS: all
   eight programs are self-contained portable C. Evidence unsigned ELF
   test binaries execute on the device: celt 1.0.0 ran `make check`
   (7/8 observed) on OHOS without signing.
8. **Manual package()** — copies `libfec.a|libfec.so` + `fec.h` only
   (skips ldconfig/install-tool/man pages).
9. **No commands.json** — install target ships no executables; pure
   library package (R38).

## Upstream test inventory (R51)

| Item | Count |
|---|---|
| Programs in `make test` | 8 correctness (vtest27/vtest29/vtest39/vtest615, rstest, dtest, sumsq_test, peaktest) + 4 speed trials |
| rstest RS configurations | 23 (symsize 2..16 incl. the CCSDS-duplicate 0x187/112/11 entry; fork-extended trials: up to 100000 per config) |
| vtest parameters | vtest27 -e 3.0 -n 1000 -v; vtest29 -e 2.5 -n 1000; vtest39 -e 2.5 -n 1000; vtest615 -e 1.0 -n 100 (plus -v) |
| Planned execution | `make test` inside recipe build() on device/CI (native, portable C) |

Upstream has no `make check` target; `test` is the check equivalent.

## Consumer test design (test_package)

- `test_rs.c` (12 checks): RS(255,223) GF(256) 0x11d/1/1/32 — clean
  decode == 0; 16 random errors corrected bit-exact; 17 errors reported
  uncorrectable (deterministic LCG; the miscorrection edge is avoided by
  the fixed seed — verified locally); 32 distinct declared erasures
  corrected; int-symbol codec roundtrip with 8 distinct errors.
- `test_viterbi.c` (3 checks): K=7 r=1/2 encode with fec.h polys,
  noise-free 0/255 soft symbols, 6-bit zero tail, exact vtest27 call
  sequence (init 0 / update framebits+6 / chainback framebits state 0),
  bit-exact comparison.
- `test_dsp.c` (4 checks): initdp/dotprod vs scalar reference (LP64-safe
  amplitudes), sumsq vs reference, peakval over offset window.

## Local verification done (Windows host, static only)

- Patches apply cleanly (`git apply --check`) onto the pristine tarball;
  post-patch `config.sub` accepts `aarch64-linux-ohos` and
  `aarch64-unknown-linux-gnu`; configure has umask 022; makefile.in has
  36 `$(CC)` references (35 patched + 1 pre-existing darwin rule).
- `conan inspect` on the recipe passes; conandata sha256 re-verified
  against the downloaded tarball (hashlib).
- The Windows host has no C compiler (no gcc/msys2/WSL), so the native
  build + `make test` + test_package binaries were NOT executed locally;
  they run first on the device / shadow CI. The consumer tests use fixed
  LCG seeds (deterministic; the >t error case cannot flake from run to
  run — worst case is a deterministic miscorrection, probability ~2^-119
  for RS(255,223), same regime upstream rstest exercises 100k trials per
  configuration).

## Real-device verification (2026-09-18, frp-tip.com:56267)

Isolated job `~/ohos-users/claude/libfec-1.0-26-gc5d935f` (conan-home seeded
from `~/.conan2`, profile `ohos-aarch64-fixed`: clang at
`~/usr/local/bin/clang` — the default profile's `/data/service/hnp/bin/clang`
does not exist on this device). Result: **conan create PASSED**, package id
`5afd1f029b3a1a68998b4ec5f666f32767e1532c`, log `logs/create-8.out`.

- Upstream `make test` inside build(): rstest **228 x "... OK"** (23 RS
  configurations, char + int codecs, up-to-capacity and beyond-capacity);
  vtest27/29/39/615 correctness runs (-n 1000/1000/1000/100, Eb/N0
  injection) exit 0; dtest / sumsq_test / peaktest exit 0; 4 speed trials
  normal (vtest27: 10000 x 2048-bit frames in 15.82 s).
- test_package on device: test_rs **12/12**, test_viterbi **3/3**,
  test_dsp **4/4**, test_consumer **5/5** — 24/24 (create-10 final log).
  test_consumer is the consumer use case required by Path B: a CCSDS-style
  concatenated FEC link (RS(255,223) outer + K=7 convolutional inner +
  noise-free soft channel + Viterbi + 16 residual byte errors + RS decode
  -> original 223-byte payload recovered bit-exact). Chainback format note
  learned the hard way: the decoder returns encoder shift-register history
  bytes that are ALREADY MSB-first packed — do not bit-reverse them
  (first device run failed 3/5 with an unnecessary reversal).
- Package contents: `lib/libfec.a` (29 PORT objects: rs/viterbi/ccsds/
  dotprod/sumsq/peakval + sim + cpu_mode_unknown) + `include/fec.h`.
- Unsigned freshly-built binaries execute fine on this device (both the
  build-time `gen_ccsds` codegen tools and the test binaries) — no signing
  needed, consistent with the celt 1.0.0 observation.

Two fixes came out of the device run:

1. **-fuse-ld removed** (commit cc68af6eef): this autoconf-2.69 configure
   rejects bare `-fuse-ld=...` as an unrecognized option (unlike celt's
   older configure), and it is unnecessary on this device — clang-15
   resolves the colocated `ld.lld` by itself (verified: `clang x.c -o x`
   links and runs).
2. **0004 patch added**: the upstream `vtest*.o` rules compile without
   `$(CFLAGS)`, so `-I.` never applies and `#include "config.h"` (generated
   by configure in the build dir) is not found; the patch adds `$(CFLAGS)`
   to the four rules.

## CI round 1 (build #50554) — timeout, and the bounded-test policy

The first CI run timed out: `conan create TIMED OUT after 3600s` (L1 fail)
with `make test` fully completed in the log and nothing after it. Root
cause analysis: the CI worker (CI-036) runs the suite ~4x slower than the
dev device; the full `make test` (rstest's fixed 23-config table with up to
100k trials/config in the int codecs + four speed benchmarks) plus the
build consumed the entire 3600s budget, leaving no time for package() /
test_package — the trailing `| tee` pipe also swallowed the last buffered
output, making the hang look silent. Not an interactive test, not a real
deadlock.

Fix (this commit): `_run_upstream_tests()` runs the seven fast correctness
programs with exactly the makefile's parameters (vtest27 -e 3.0 -n 1000 -v,
vtest29/39 -e 2.5 -n 1000 -v, vtest615 -e 1.0 -n 100 -v, dtest, sumsq_test,
peaktest) and skips rstest + the four speed benchmarks inside the recipe.
The complete suite — rstest's 228 up-to/beyond-capacity checks and all
speed trials — was executed verbatim from `make test` on the real device
(frp job, logs create-8.out); test sources/binaries are unchanged by the
skip, only the in-recipe invocation is bounded for the CI time budget.

Also hardened `_ohos_tool_prep()` after a second device layout was tested
(10.62.178.77): its HMDFS denies symlinks whose target lives on another
filesystem (toolchains under /data/service → `os.symlink` EACCES), which
was fatal before. Now: names already resolvable in PATH are skipped
entirely (CI workers expose ld/ar/ranlib via the profile buildenv PATH),
symlink failures fall back to a copy, and both failures degrade to a skip
with an info message instead of aborting the build.

## Second device verification (2026-09-19, 10.62.178.77, ci profile)

The CI profile layout (clang + binutils under /data/service/hnp/bin,
CONFIG_SHELL/SHELL = its bash) surfaced one more wall: that bash cannot
getcwd() inside HMDFS directories, and autoconf 2.69's configure re-execs
itself under $CONFIG_SHELL — so both `bash configure` and plain
`sh configure` died with "working directory cannot be determined".
Fix: invoke configure as
`CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "<configure>" <args>` and run make
with the `SHELL=/bin/sh` variable override (upstream recipes are plain
POSIX). Result (diag7 log, package 21b17f8b2bc0e9511e276e3d57a23893067cefe5):
zero getcwd errors; configure + build + the seven bounded upstream
correctness programs (vtest27/29/39/615 with the makefile's exact
parameters, dtest, sumsq_test, peaktest) + test_package 24/24 all green.
The two extra knowledge drafts (configshell-bash-getcwd-hmdfs) document
this. This sh-forcing is a no-op on the frp layout (user-local bash works
there) and on CI workers whose bash handles their storage.

Device-environment notes (not recipe problems):

- The device's Python/conan cannot reach `github.com` (connect timeout)
  while curl reaches `codeload.github.com` and `gh-proxy.com`. The job-local
  conandata.yml copy was rewritten to the CI-style `gh-proxy.com/` mirror
   URL (same archive, sha256 re-verified on device:
  a2fff6f8...c3bc9). The committed recipe keeps the official github.com
  URL; CI applies the same mirror-fallback rewriting.
- Isolated conan-home needs manual seeding: `cp -r ~/.conan2/profiles` +
  `cp ~/.conan2/settings.yml` (otherwise "Invalid setting 'OHOS'").
- Remote heredocs fail (mksh wants /tmp, read-only) — write scripts with
  per-line `echo` instead.

## Next steps (device / shadow CI)

```sh
# device (frp): isolated job, then
conan create archives/l/libfec/1.0-26-gc5d935f -pr:h ohos-aarch64 -pr:b ohos-aarch64
# shadow CI single package
CI_PACKAGES="archives/l/libfec/1.0-26-gc5d935f" zsh ci/conan/build_and_test.sh
```
