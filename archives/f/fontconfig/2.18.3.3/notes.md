# 2.18.3.3 runtime delivery candidate

This is a locally tested candidate, not a formally finished or published package.

## Latest complete target result, 2026-10-06

Fresh actual Conan create private-r7 rebuilt the five-patch recipe with RC0;
RREV f517dbf187eb04b6667ac7478b5b3b19,
PID eb8a1377e7d30f9f68371d8f4bd2af8e42522628,
PREV 6c76f12d55688ea0115a7deec3a3e0de. Expat remains a private dependency,
not an official publication.

One immutable transaction upstream-r12 on10.62.201.39:2222 executed the
complete500-case configured inventory:15 C passes+485 pytest passes,
0fail/0error/0skip. Runtime7/7, current candidate Harmony test1/1,
setup-failure negative controls4/4. The launch was consumed once and all28
receipts replayed successfully; owned processes cleared in two scans.

The multithread test now uses configuration sentinel state instead of an
unreliable freed-address comparison. Its unchanged100-thread workload passed
five times in r8; deliberately retaining the current config was rejected.

The five formerly skipped cache tests retain their font-list/cache-count,
metadata/basename and warning assertions. On OHOS, an explicit private
directory-view backend replaces only the namespace-dependent fixture setup.
The parent fixture's view is restored before expectation enumeration, and an
absent dummy dir avoids overwriting remap-dir or creating extra caches.
Linux retains bubblewrap. These5/5 are adapted cache-semantic passes, not a
claim that kernel namespace/security isolation works. r9/r10 failures remain
archived and were not erased or merged into the r12 totals.

The frozen execution tree was5f77b117ba953c62f22dcd0655d1a4f3583cad14;
HEAD/base remains b95978a4750e7aa9a3d49af148bb3bbedf81051d. Subsequent
changes to notes/manifest/knowledge record these results only; runtime inputs
are unchanged. Local evidence report (ignored diagnostic artifact, not CI input):
reports/upstream-current.md.

After target PASS a new isolated official check still could not resolve
expat/2.8.5: graph/install RC1 with Unable to find expat/2.8.5 in remotes.
The independent fresh freetype/2.14.3 control installed successfully. Formal
finish/Pre-PR remains blocked only on this publication gate; manifest stays
failed and no .ci-result.json is manually created. No PR/push/Review/CI,
submission, repository upload or repeated claim was performed.

The following sections retain earlier observations as history, not latest state.

The target has /system/fonts but no /etc/fonts/fonts.conf or /usr/share/fonts.
Use the upstream Meson font-directory options, preserve aliases and enabled
conf.d rules, materialize enabled template links as relocatable regular files,
and deliver package-specific FONTCONFIG_FILE/PATH via Conan runenv metadata.
The configuration uses only an XDG application-owned cache, not /var or the
immutable Conan package. Secure native applications that ignore environment
variables must load the supplied configuration explicitly using FcConfig APIs.

The test package now links and calls the real configuration/discovery/matching
APIs and rejects invalid/missing explicit XML. It does not count dlopen as font
matching, nor treat a missing matched font as success. This candidate retains
CLI and upstream tests; errors are no longer suppressed with ignore_errors.

Latest Expat 2.8.5 is currently missing from the official remote. User authorizes
local preparation before publication; formal W0, target execution, full upstream
tests, finish and Pre-PR remain separate gates. No old dependency/cache substitutes,
artifact uploads, .ci-result.json fabrication or other authors' PR changes.

## Actual target observations (not formal publication or current-package W3)

Task 14915 was imported and claimed once via the in-app contribution browser.
An immutable target transaction executed configuration, font discovery/matching,
missing/malformed configuration rejection, relocation and private cache checks:
7/7 passed; a generic private file round-trip was historical evidence, not a
HarmonyOS-specific capability proof. All evidence roots were kept;
owner-only two-scan release and receipt replay passed.

The complete configured upstream entry list executed on OHOS in upstream-r2:
15 C entries passed; pytest returned zero with 459 passed and 26 skipped, no
failure/error. Thus selected upstream cases are 474 passed / 500 collected,
with 26 conditional skips (3 prior-version baseline, 18 optional JSON test
executable, 5 bubblewrap). Do not label this 500/500 or zero-skip coverage.

Two original C regressions hard-coded /tmp. One returned zero on mkdtemp
failure, so its first zero RC was rejected after reading the real stderr.
Source repairs use bounded TMPDIR-aware templates, preserve the test body, and
make that setup failure nonzero. The official refresh-patch generator produced
two per-file patches and passed dry-run. A task-private Windows Path rendering
adapter was necessary because the unchanged generator did not normalize
backslashes in patch filenames/headers. No framework source was modified.

The exact repaired C sources passed on target before patch packaging. Candidate
recipe/patch inputs have now changed, so the old root package revision/target
identity is not a current formal recipe W3 PASS. Fresh package validation and
formal Expat publication remain pending; manifest stays failed.

## 2026-10-06 baseline and test-package closure

Official fontconfig 2.18.2 was cross-built only as a previous-release test
fixture (cache version 12). It does not replace the current provider or lower
the dependency versions. All three actual cross-version compatibility cases
passed in immutable upstream-r6. The full r6 inventory remained 500:
494 PASS, one FAIL (test_mt_fccfg), five sandbox SKIP. A diagnostic r7 repeated
the multithread case successfully with FC_DEBUG=16, but does not erase the r6
failure or prove its cause. No whole-suite PASS is claimed.

The new test_package HARMONY_TESTS.yml and projected_config.py are now called
by the real Conan test method. The frozen current-script r7 execution emitted
HARMONY_TEST_PASS=1/1 after checking projected storage ownership, exact UTF-8
configuration bytes, preserved conf.d and native font matching. Its configured
consumer also passed seven runtime assertions. These are not formal W0/finish.

Bubblewrap 0.13.0 was compiled with the official retrieved libcap 2.78 static
binary. Test-tool-only portability fixes used getcwd and separated a duplicate
kernel-UAPI storage type; security checks were not disabled. In this SSH domain
the original bwrap rejects inherited capabilities. A child-only capability-drop
launcher then terminated with SIGSYS (-31), leaving the five real sandbox cases
skipped. This observation is not proof of which syscall was denied, and is not
a universal platform limitation or an acceptance waiver.

Both consumed runs were read back and released with two clean owned-process
scans; inputs, logs and hash-chain evidence remain preserved. Latest fresh
official expat/2.8.5 graph/install --build=never still fail resolution. No
commit/push/PR/Review/CI/submission was performed and manifest remains failed.
