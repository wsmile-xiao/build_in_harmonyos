# xev 1.2.7 test report

## Counting method
The common unit is a logical assertion executed on the OHOS device. Upstream xev 1.2.7 ships
no automated test suite, so the upstream count is established statically against the extracted
source tree and by the harness's own upstream probe; the executed count comes solely from the
test_package consumer script running the packaged binary on the real device (HarmonyOS aarch64).

Static/registered counts are counted per-file with line-anchored grep on
「~/tmp/ch/home-B-xev/p/xev5c6205c0ea6f0/s」— the upstream tree that this round's W3 run
extracted from a **cold** source() call (see 「Cold source proof」 below; xev.c is 48207 bytes,
sha256 fb6ecd81084d83751ba0e3f3ca0ee6f27cfdf8e8e21f0b585c9c29848a5aaf63); executed counts are read verbatim from
「reports/w3-local-ci.log」. No static number is reported as a measured number.

| Symbol | Meaning | Value |
|---|---|---:|
| N_static | upstream source assertions (line-anchored) | 0 |
| N_registered | TESTS/ctest/meson test() registrations | 0 |
| N_executed | device assertions actually run | 4 |
| N_consumer | consumer programs | 1 |
| N_assertion | assertions in the consumer program | 4 |

## Results

| Environment | Test group | Passed | Failed | Skipped | Disabled | Assertions | Result |
|---|---|---:|---:|---:|---:|---:|---|
| OHOS 6.0 armv8, local W3 (home-B-xev) | Upstream suite | 0 | 0 | 0 | 0 | 0 (no suite) | SKIP / no_tests |
| OHOS 6.0 armv8, local W3 (home-B-xev) | test_package consumer | 4 | 0 | 0 | 0 | 4 (checks=4 failures=0) | PASS |
| OHOS 6.0 armv8, local W3 (home-B-xev) | L2 raw smoke (--version/--help) | 0 | 0 | 1 | 0 | 0 | SKIP |
| OHOS 6.0 armv8, local W3 (home-B-xev) | Destructive negative test (R34/L1e) | 1 | 0 | 0 | 0 | 0 | PASS |

## Raw evidence (verbatim, line numbers within this round's reports/w3-local-ci.log — 523 lines,
## bound by the .ci-result integrity_hash f08ae7bf497cb201 / log_sha256
## 1b9127acbf8bccd5e3c9df9f2508c158d21ca8bebd3aaca570cc1293da203253 quoted in ## Integrity below;
## every number was re-checked with 「sed -n 'Np'」 after the cold re-verification)
- L99-L101 — W3 pre-download fetched the source from the official URL:
  「found 2 source URL(s)」 / 「[try 1/1.1/3] xev-1.2.7.tar.gz ← https://xorg.freedesktop.org/pub/individual/app/xev-1.2.7.tar.gz...」 /
  「[ok] xev-1.2.7.tar.gz (176KB) via mirror 1」 (= 180306 bytes; "mirror 1" is the framework's loop-index label —
  the pub/ path does not match its mirror-list regex, so candidate 1 is the official URL itself)
- L102 — 「[cached] xev-1.2.7.tar.gz (0KB)」: the archive/ entry hit a stale 162-byte 404 page left in the
  pre-download cache, which is exactly why pub/ must be listed first
- L207 — 「xev/1.2.7: Calling source() in /storage/Users/currentUser/tmp/ch/home-B-xev/p/xev5c6205c0ea6f0/s」
- L208 — 「xev/1.2.7: Sources correctly downloaded from …/.build-cache/predl_cache/2e2a1c23_xev-1.2.7.tar.gz」
  (that file is the 180306-byte official tarball fetched from the pub/ URL; Conan verifies sha256 per URL entry)
- L436 — test_package RUN command actually executed on device:
  「xev/1.2.7 (test package): RUN: "/bin/sh" ".../test_package/test_xev.sh" ".../p/b/xevc2ac95246249e/p/bin/xev" "...libXau…:...:...libXrandr.so.2.2.0"」
- L441/L443 — 「[test 1/4] xev -version」 → 「PASS: xev -version reports 'xev 1.2.7' (exit 0)」
- L444/L446 — 「[test 2/4] xev --version」 → 「PASS: xev --version reports 'xev 1.2.7' (exit 0)」
- L447/L468 — 「[test 3/4] xev -help」 → 「PASS: xev -help prints usage banner (exit 0)」
- L469/L490 — 「[test 4/4] xev -Zz (unrecognized option -> nonzero exit)」 → 「PASS: xev -Zz rejected with usage + nonzero exit (rc=1)」
- L491 — self-proof line: 「OK: all 4 checks passed」
- L492 — 「HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xev.sh","discovered":4,"passedCount":4}」
- L494 — 「HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"make -n check (no check target)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"xev 1.2.7 上游无测试套件…"}」
- L495 — 「[ok] xev/1.2.7 — conan create passed」
- L497 — 「[ok] L1a: test_package was executed by conan create」
- L503/L505 — the locator for the R34/L1e row of the Results table above:
  「[step] L1e: Destructive negative test (R34)...」 →
  「[ok] L1e: Negative test confirmed — test genuinely depends on xev」.
  Its sabotage action line sits at L504 (bin/ moved away), which is what proves the consumer test
  really depends on the built xev binary. Re-checked on this round's log with sed -n 503p and
  sed -n 505p; the round-1 suggestion to cite L507 is wrong — L506/L507 are the L2 smoke step and
  its 「[warn] L2: xev --version/--help failed (non-blocking)」 line.
- L502/L513 — 「[ok] L5: bin/ has content」 / 「L5_RESULT=pass: bin/ has content」
  (artifact check on bin/xev; see ## Integrity for the measured file).
- L509/L510/L511 — 「L0_RESULT=pass: all checks passed」 / 「L1_RESULT=pass: upstream tests + test_package executed」 /
  「L2_RESULT=skip: xev version/help failed」
- L521/L522 — 「Pass rate: 100.0% (1/1)」 / 「[step] All packages built and tested successfully ✅」

### N_static / N_registered proof (device commands, verbatim results)
- 「grep -cE '^[[:space:]]*assert[[:space:]]*\(' xev.c」 = 0
- 「grep -oE 'assert[[:space:]]*\(' xev.c | wc -l」 = 0
- 「find . -maxdepth 2 -type d \( -name tests -o -name test \)」 → no output
- 「grep -nE 'TESTS|check' Makefile.am」 → no match (rc=1); only 「SUBDIRS = man」
- 「grep -nE 'TESTS *=' Makefile.in」 → no match (automake emits empty 「check: check-recursive」@825, no registered cases)
- 「grep -nE 'AC_CONFIG_TESTDIR|_TESTS|CTEST|tests' configure.ac」 → no match (rc=1)
- 「grep -nE '^[[:space:]]*test[[:space:]]*\(' meson.build」 → no match (rc=1)

### L2=skip measured evidence (why it is honestly kept as skip)
The harness L2 smoke (ci/conan/build_and_test.sh:1676-1706) runs the packaged binary **raw**
with 「timeout 15 "$bin" --version </dev/null >/dev/null 2>&1」, without conan's runtime library
environment. Re-measured in this round against the binary produced by the cold W3 run,
「/storage/Users/currentUser/tmp/ch/home-B-xev/p/b/xevc2ac95246249e/p/bin/xev」 (43456 bytes):
- raw 「--version」/「--help」 exit code = **127**; verbatim harness-identical probe
  「env -i timeout 15 "$BIN" --version </dev/null >/dev/null 2>&1」 → **127** as well. First real error line:
  「Error loading shared library libXrandr.so.2: (needed by /storage/Users/currentUser/tmp/ch/home-B-xev/p/b/xevc2ac95246249e/p/bin/xev)」,
  followed by 30 more 「Error loading shared library …」 and 34 「Error relocating …: symbol not found」
  lines (XOpenDisplay and the whole DT_NEEDED set unresolved).
- Same binary **with** the conan dependency LD_LIBRARY_PATH taken from L436 of this round's log
  (7 dependency p/lib dirs): 「xev --version」 → 「xev 1.2.7」, exit **0**; 「xev -version」 → 「xev 1.2.7」, exit **0**.

Conclusion: L2 skip is caused by the bare smoke probe missing the runtime library search path
(loader failure at exit 127 before main), NOT by the -version/--help path failing to return before
XOpenDisplay (source layout xev.c:1352/1363 puts(PACKAGE_STRING) both precede xev.c:1384
「dpy = XOpenDisplay(displayname);」). It is kept as skip; not converted to pass and not removed
from the denominator. Precedent archives/x/xbanish/1.8 is likewise 「L2=skip」 and not written as pass —
that borrowed example is **not** in the mainline nor in this PR's base: in this worktree
「git ls-files archives/x/xbanish」 prints nothing (ls archives/x has no xbanish entry) and the path
exists only on the unmerged branch 「origin/feat/xbanish-1.8」, so it must be cited with that branch
qualifier instead of being looked for in the main tree.

## Consumer scenarios
1. 「xev -version」 prints PACKAGE_STRING containing "xev 1.2.7", exit 0 (L443).
2. 「xev --version」 prints "xev 1.2.7", exit 0 (L446).
3. 「xev -help」 prints the usage banner, exit 0 (L468).
4. 「xev -Zz」 (unrecognized option) prints usage and exits nonzero (rc=1) (L490).

## Not covered
- GUI event loop: XNextEvent main loop, do_RRNotify_* XRandR event handlers, window drawing.
  Reason: requires a real X server plus interactive input; not executable in headless CI.
- The raw L2 smoke path (see above) — covered instead by test_package with proper LD_PRELOAD.

## Cold source proof (this round's re-verification)
The previous W3 run never called source() (「Calling source」 count = 0 in that log), so its green
result proved only compilation, not that conandata.yml can obtain the correct sources. This round:
1. conandata.yml was switched to two official paths on the **same** official host, with
   「xorg.freedesktop.org/pub/...」 first — that path does not match the framework pre-download
   mirror-list regex, so it is fetched directly from upstream (archive/ is kept only as fallback).
   The former 「www.x.org」 entry was **removed**: on this build host it fails deterministically with
   「curl: (60) SSL: no alternative certificate subject name matches target host name 'www.x.org'」
   (http=000, size=0, rc=60), so it must not be the first dependency URL. No "two official domains
   agree" argument is used anywhere in this package.
2. Live probe from this host (2026-09-24 03:16, record: ~/tmp/uc2/xev-cold/02-url-probe.txt):
   「https://xorg.freedesktop.org/pub/individual/app/xev-1.2.7.tar.gz」 →
   「http=200 redirects=0 size=180306」, 「gzip compressed data」,
   sha256 「e75e35e225acdfe648a73e75aedabccf47f46bdab6590f43428be97b2876b94e」 = the delivered value.
3. 「conan-verify」 alone then showed G0-G4 PASS / RC=0 **and** a cold fetch — the two verbatim lines
   「Calling source() in …/p/xev6d29aa59a5def/s」 and
   「Sources correctly downloaded from https://xorg.freedesktop.org/pub/individual/app/xev-1.2.7.tar.gz」
   are preserved in the stable snapshot 「~/tmp/uc2/xev-cold/20-run.txt」 lines 17-18
   (the transient 「reports/conan-create.log」 holding them was later overwritten by finish's own
   internal verify pass, so it is deliberately not cited as the locator).
4. To make the deliverable W3 log itself cold, the recipe cache was cleared with the official
   command 「conan remove xev/1.2.7 -c」 (「Removed recipe and all binaries」 for both revisions)
   **after** confirming the authentic tarball is present and verified on this host
   (「~/tmp/builds/xev-1.2.7.tar.gz」, sha256 identical to the delivered value; the shared
   「~/tmp/ch/dlcache」 holds no xev entry — measured count 0 — so nothing there had to be touched).
   「gate.sh」 returned GATE_PASS, then the build slot ran 「finish xev 1.2.7 built」.
   Result: 「grep -c 'Calling source' reports/w3-local-ci.log」 = **1** (line 207), sha256 check passed
   (line 208 onwards, 「conan create passed」 at line 495).

## Integrity
- Official source SHA-256: 「e75e35e225acdfe648a73e75aedabccf47f46bdab6590f43428be97b2876b94e」
  (real tarball, 180306 bytes; this round the winning URL answered with http=200 and **0 redirects**;
  not modified, and no checksum/verification logic was relaxed to make any gate pass).
- conandata.yml sources: two official paths on the same official host, predownload-safe order
  「https://xorg.freedesktop.org/pub/individual/app/xev-1.2.7.tar.gz」 first then
  「https://xorg.freedesktop.org/archive/individual/app/xev-1.2.7.tar.gz」; 「patches: {}」;
  no third-party proxy prefix, no local-path URL type, and no scheme-bearing URL string inside the
  comments (the framework harvests those too) — R39.
- Verification command: 「sh ~/tmp/uc2/gate.sh」 then
  「sh ~/tmp/uc2/build-slot.sh --kind short --wait 3600 --mem 2500 -- python3 scripts/ohc-run.py finish xev 1.2.7 built」
  (W3 local CI) on HarmonyOS aarch64, CONAN_HOME=~/tmp/ch/home-B-xev, profile ci/conan/profiles/ohos-aarch64.
- .ci-result.json of this round: timestamp 「2026-09-24T03:27:53.370249」, exit_code 「0」,
  step 「W3_local_ci」, integrity_hash 「f08ae7bf497cb201」, log_sha256
  「1b9127acbf8bccd5e3c9df9f2508c158d21ca8bebd3aaca570cc1293da203253」. The delivered conandata.yml
  mtime is 「2026-09-24 03:27:53.336442031 +0800」 (the framework restores the official URLs when W3
  exits), i.e. the evidence was produced **after** the recipe file it binds to.
- Known non-blocking noise, left untouched: finish's Step 3 clean-verify prints
  「G0: 找不到原始 tarball」 because it only looks in the repo root / a .build-context file; the
  previous round's log shows the identical line, and it is unrelated to the W3 source retrieval above.
- Device: HarmonyOS PC aarch64 (8 cores / 31G). Conan 2.29.1, clang (OHOS), os=OHOS/arch=armv8.
- Resource probe (memcap-run --probe): 「peak=205MB」, recorded at line 164 of
  「~/tmp/uc2/xev-diag/06-finish-20260924-022954.txt.prev-20260924-0300」 (a finish run of this same
  recipe wrapped in the probe; this round's prescribed command ran unwrapped, so no new number was
  invented). manifest.yaml carries no max_rss_mb field, and no file under origin/main:archives contains
  that literal at all (verifiable: 「git grep -l max_rss_mb origin/main -- archives」 → no match, rc=1;
  re-run on this round's worktree). Stated with that scope on purpose, because the naive command
  「grep -rl max_rss_mb archives/」 run in this worktree **does** return two files — this report and
  notes.md, i.e. the two prose files that describe the probe value; neither is a manifest.yaml, and no
  other package is involved. Outside the mainline convention, the unmerged branch
  origin/feat/xbanish-1.8 has its own max_rss_mb entry (archives/x/xbanish/1.8/manifest.yaml line 73).
- No upstream source or test file was **patched**: patches/ is empty, conandata.yml declares no patch and
  manifest.yaml lists none. What the recipe does instead is rewrite the upstream **autoconf-generated
  configure script in place at build time** — conanfile.py:135-162 (_rewrite_configure: umask 077 →
  umask 022, plus a PWD fallback for the pwd / ac_pwd probes) and conanfile.py:111-133
  (_prepend_toolchain_path: prepends the compiler tool directory to the process PATH), with build()
  chdir-ing into the build folder and presetting PWD (conanfile.py:164-173). That is functionally
  equivalent to a patch, so the empty patches/ must not be read as "zero source modification". No test
  file was added to or removed from the upstream tree (there is none upstream, see N_static above).
- The package installed the single 「bin/xev」 executable (self-signed in package()). Measured facts
  behind commands.json declaring binary=true for this version: make install (L342), llvm-objcopy and
  binary-sign-tool self-sign (L360, L362), 「[ok] L5: bin/ has content」 (L502) and
  「L5_RESULT=pass: bin/ has content」 (L513); the packaged file
  「/storage/Users/currentUser/tmp/ch/home-B-xev/p/b/xevc2ac95246249e/p/bin/xev」 measures 43456 bytes,
  mtime 2026-09-24 03:27:51, sha256
  「23941ea4a80a74e1d23240d15bffcef65a2d6d92c383251412e020e26f4ea28b」, and file(1) reads it verbatim as
  「ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped」.
