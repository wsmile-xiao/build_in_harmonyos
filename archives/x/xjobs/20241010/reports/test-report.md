# xjobs 20241010 test report

## Current affected evidence (2026-10-03 documentation; H1 runs 2026-10-02)

This revision preserves the tested software bytes from ZIP `f48430b98b8eaaee022ef2e85aff15d01215dbaedb569506676a0c3cb2194be5`. Patch0001 propagates a child failure only with `-e`; default mode retains the upstream exit contract while counting failed jobs. Patch0006 changes the upstream test helper `testdummy`: `command -v` selects by status, the literal `gsleep`/`sleep` command receives the quoted delay, and a sleep dependency error exits 2 before the original expr branch. **Upstream tests modified: yes, helper only.** Original `runtest1.sh`, ten `rand()*10` inputs, `-j8` and intentional expr/echo/0-or-1 results are unchanged.

- H1-021: real helper0.05 -> rc1 after successful sleep/expr; helper4.5 -> rc0, 4.572179063 seconds; invalid duration -> rc2 before expr. One forced-source Conan create rc0 with six patches and unchanged consumer8/8. Default-mode before/fail/after all finished, one failed/two succeeded, parent rc0; exact worker17 is source inference, not directly observed wait status. `-e` failure/nonzero/stop is covered by the unchanged consumer.
- H1-025: one original registered `make test` in the same new build, rc0, 11.362298594 seconds, ten started/finished tasks, final `0 queued, 10 finished, 3 failed, 0 running`, maximum running8. Negative values `3.06394`, `3.32195`, `1.00887` and failure count agree exactly with ten once-only original expr references. Three deliberate negative child results are expected test behavior; this is **registered upstream1/1 PASS**, not ten positive child successes or consumer substituted for upstream.
- Package/build ELF64 AArch64: 84,416 bytes, SHA256 `33e1dda1bb9915cc24ec31bd069b9fb890394cef3d2923ab4f8dd29b7b0cb872`; package actual private mode0700. Reference `xjobs/20241010#e6b7c108a7f858c864a25a56c52504ea:6b129b068851896169fae42d399fa922d239ce8a#c493f82bea3715cc00c98c744ab274a7`.
- Environment: existing HiShell UID/GID20020084, original private ROOT/mode/labels and Conan home; independent normal-sh profile SHA `d311f0d72d0b81a1e7f875bcd4ef1957ac0db97c38df135566eddceb508ff3af`, host/build identical. No shared profile or recipe shell override is submitted. H1-025 uses the system-sh explicit-Python recorder wrapper, real gawk unchanged argv/hash, complete byte forwarding, explicit DEVNULL, exclusive files and bounded collection. H1-021 inherited stdin; that difference is disclosed. Recorder timeout/TERM branch was not deliberately exercised.
- Current counting: one registered upstream flow plus one Conan consumer flow (eight checks), N=1 / adapted flows=2. Historical standalone framework staging/version probe remains evidence of compatibility, separately disclosed as a diagnostic, not an additional registered test flow. No upstream case or consumer assertion was removed; previous tables counting that diagnostic as a third flow are historical.
- H1-021 RESULT SHA `bf25fe443b60986a3947e7d9291d6baca58483a9233717eabd48c57d271116f8`; raw384371B/95 files/94 manifest payloads SHA `730d50c41dbcf0e1f73f0da444531ba08d1aaec1c417a17d0bde6cb6a48a82e2`.
- H1-025 RESULT SHA `dd8e2063e7ed9f05558fcd68e398ee7ba6ce4f479951a0b379a654f34fadd341`; raw29742B/97 files/96 manifest payloads SHA `5161e0d1907a5f9e4a00544d44114e658fa0a9307731b24a6d3a6b6e0de99b8c`. All listed payload sizes/hashes were independently checked; 32 recorded PIDs are gone, cleanup signals=[], slot released.
- Independent affected source review SHA `9ea582868e020ac0b383a22fd7fb72f3897e45012a627da9bd9029273804a143` found P0/P1=0 for this 0001/0006 candidate. Older W4/audit-result artifacts retain their old input scope; this is combined review coverage, not a new full W4 claim.

**Current official W3 software stage:** PASS on the exact six-patch candidate, from one c611 step35 call in W3-v2 on 2026-10-03. Setup/build/worker rc0, natural official writer, actual consumer8/8 and AArch64 binary verified. Collection remains UNKNOWN_OR_FAILED_STOP/capture_pass=false due to four proc reads; independent post-terminal evidence establishes current no residual processes and slot release, not complete historical identity sampling. W3-v1 UNKNOWN is retained. Hosted CI66795 passed old public head88493c8 with five patches only; new revision hosted CI/effective review submission/merge/points require separate results. Historical H1-011/021/023 and framework/CI failures remain unchanged.

## Current official W3-v2 evidence (2026-10-03)

- Fixed input: tree `5d1e7cb607e831d8250b362e64b51d3bc4f69e57`, ZIP `0b998b146ca3ba30b3503d458723d43029826a43a846a3e90953a19ec2330779` (156823 bytes, 20 members), 19 xjobs paths, six unchanged patches; complete real JUNK_PR_DIFF SHA `ac8f61821d407151e081d6f4d926465c86f2b9e5d88f00ae03ab3f862c89c95a`.
- Framework: original c611 commit `c611f7d61b422eda200fc49481cf0d404e63f10c`, clean private clone/no alternates, named private normal-sh profile SHA `d311f0d72d0b81a1e7f875bcd4ef1957ac0db97c38df135566eddceb508ff3af`; official scripts/old12 inputs/baseline markers unchanged.
- One official `FinishPipeline.step35_local_ci()` call; worker47406 rc0, 54.278913125 seconds, no timeout. Setup rc0/build_and_test rc0; original G0/KC/JC and L0/L1/L2/L4/L5 pass. Six patch application, forced-source Conan create and actual test_package8/8 ran; destructive L1e confirmed test dependency. These are actual v2 results, not copied021 results.
- Natural official `.ci-result.json` SHA `763aaf5204d7dde6a377a03c8fe98c166efded24addd5258477c9f2b21d09f23`, exit_code0/W3_local_ci/xjobs/20241010; timestamp2026-10-03T02:58:22.603930 yields integrity `a226a354e6ae1144`. Original w3-local-ci.log 19438 bytes SHA `433a4f8eabf0df2d956f504b9f5c9a9e2b3af142bc2b2139ec4a1bbefc9c47fb` matches writer. Result file stays evidence only; it is not manually rewritten or included in PR.
- Actual reference `xjobs/20241010#99a9ec1e9b0b1fa38fae849e0861661c:6b129b068851896169fae42d399fa922d239ce8a#c493f82bea3715cc00c98c744ab274a7`. Actual package ELF64/little-endian/AArch64(e_machine183), 84416B/mode0700/SHA `33e1dda1bb9915cc24ec31bd069b9fb890394cef3d2923ab4f8dd29b7b0cb872`, same digest as021. Original025 upstream1/1 evidence therefore remains tied to the same software bytes; no new upstream test was run in W3-v2.
- Pre-download logged missingcurl three times, then official WARN/fallback and Conan source cache succeeded. No curl installed/framework changed. This does not prove source download on an empty new machine.
- Outer collection has four recorded errors:48099/cwd/EINVAL,48589/argv/EINVAL,48589/cwd/ENOENT,49730/stat/EINVAL. It did not terminate the worker early; signals=[], rc0 retained. Ownership sampling incomplete and capture_pass=false/UNKNOWN_OR_FAILED_STOP remain. Do not label the errors as established exit races or make the whole collection contract PASS.
- Independent postflight:339 recorded identities exited, collector47403 and error PIDs absent; sameUID command/cwd/ps scan found no v2 residuals, old12/candidate19/official5/marker4/config3/profile unchanged. This establishes current slot release without inventing unobserved historical process identities. W3-v1 UNKNOWN/old blocked Goal are retained; no replay requested.
- RESULT SHA `9b69165073cc8458f02a1149f96dd9118faaf9a532796ff53ede731856509ea8`, validation SHA `5f92a9e2244b2a070897a7da9457a069053f59be6911b1b6d847c5c78e4704a0`, raw-evidence.tar.gz 884414B/153members/152payload SHA `eea9f914285a49112a35aaba9874a539ed65b91bb3f2cfc05918bf1be3329769`; original H1 validation checked payload size/SHA/mode/UID/GID. Author read actual stage/writer/log/consumer/binary and result boundaries; no device execution by author.
- Publication metadata updates only notes/report after this frozen W3 input. Six patches, recipe, conandata, source and consumer remain byte-identical; metadata changes do not claim the same entire archive/tree or future recipe revision. Independent terminal delivery review SHA `095cbcb957e2da234ad313cf045377996c6a6a8688ac9866a2b1b97e19bb25b8` concluded PASS_WITH_RETAINED_CAPTURE_UNKNOWN/P0P1=0; older source W4 and affected review retain their scopes. Current-head hostedCI, review/opinion closure, submission, merge/task/points remain separate.



## Historical evidence (input/date boundaries retained)

Date: 2026-09-29

## Scope and fixed candidate

This report records H1-016 as historical evidence for its earlier CRLF ZIP and H1-017 as the one-time official W3 run on the frozen LF candidate: ZIP SHA-256 `27e5f6c68a4edefa918fed25bedba4c4c78e4549118f94eef6afb4f2e0eee134`, sidecar `1b60252b64c7f51deec2c41372ac4f88f5c8b623396f415ccda0460fa4686abb`, and 17-path PR diff `493835d40a316a5d36d653c45cffd22912d2d46beefd70da8d6b3077ff81cb2f`. H1-017 used a fresh unmodified c611 checkout and returned RC=0; its official writer created `.ci-result.json`, Conan create succeeded, the consumer passed 8/8, and the binary was AArch64 ELF64. After that run, only this report, `notes.md`, and `audit-result.json` were edited to record evidence and review status; the recipe, source, patches, manifest and tests were unchanged. H1 evidence applies to its fixed pre-disclosure ZIP and build inputs, not byte-for-byte to the subsequently re-bundled documentation revision. Full `finish`, G0 and official hosted CI are not claimed.

## Test inventory and actual results

| Check | Scope | Result | Evidence in this report/candidate |
|---|---|---|---|
| Upstream `make test` / `runtest1.sh` | Ten randomized dummy jobs with `-j8` | Historical #011 run once; RC=2, 3 failed and 7 succeeded. Not rerun. | Fixed input SHA-256 `9d135dfc6990bc11012fe7596542bd9cacf38622d412ee4a2a7d23117cf1c1a9`. The deterministic failure-propagation and `-e` behavior checks are visible in `test_package/functional.py`. |
| Native configure/make/install and staging probe | HarmonyOS AArch64 | H1 #011 passed; `--version` probe reported `verified=1 failed=0`. | ELF: AArch64 ELF64, 84,416 bytes, SHA-256 `6314e82319f8ad46d6a1c9ce429d95073e4281cdba59ea77716b7f098c3a2afe`. |
| Conan create and deterministic consumer | OHOS AArch64 recipe and package | H1-017 exact frozen step5d input: Conan create succeeded; deterministic `test_package` passed 8/8; `bin/xjobs` was AArch64 ELF64 (84,416 bytes, SHA-256 `b11d822a7fc64ee4e8eede621ee74d8dd825a42250a3c8aace276be573a5de01`). | H1-017 result is bound to ZIP `27e5f6c68a4edefa918fed25bedba4c4c78e4549118f94eef6afb4f2e0eee134`; full evidence archive SHA-256 `dfdd0342f9d9191240e87be545797fb63dbf7bee53654ab178f6263a43d1f058`. H1-014 and H1-016 remain historical for their inputs. |
| Formal framework local CI W3 | c611 `FinishPipeline.step35_local_ci()` on `xjobs/20241010` | H1-017 ran once on the fixed LF ZIP `27e5f6c68a4edefa918fed25bedba4c4c78e4549118f94eef6afb4f2e0eee134`; RC=0, setup/build_and_test succeeded, junk check used `prdiff (17 个文件)` with 0 errors, Conan create succeeded and consumer passed 8/8. The official `_write_ci_result(passed=True)` wrote `.ci-result.json`; its `integrity_hash` and log SHA were independently verified. `make -j1`; randomized `make test`/`runtest1.sh` was not invoked. | W3 log SHA-256 `ef8745e5f633ae747788d86f27d98b813c7543c527d57c5a7e0cfef17d79033a`; `.ci-result.json` SHA-256 `2b6f0e3c6c494e36e0134d94fb3d15793ba114169d82a325fc2e8a929e9ceac0`; full evidence archive SHA-256 `dfdd0342f9d9191240e87be545797fb63dbf7bee53654ab178f6263a43d1f058`. |
| Global knowledge completeness W5 | Whole c611 knowledge graph, not xjobs-only paths | RC=1; retained as the actual exit result. The function reported empty `root_cause` for E219, E253, E305, and empty `rec_approach` for E305. Pairing 541/541 and graph validation passed. | The c611 raw output is retained in the H1 evidence bundle; global failure is disclosed and is not represented as an xjobs candidate failure or waiver. |
| Candidate knowledge-gap W5 | xjobs 20241010 step5c candidate only | RC=0 on step5c input. At that time `notes.md`: total/pending/failed = 0/0/0; manifest knowledge_count=4, unreferenced=0. Official function generated `.knowledge-done`, SHA-256 `f93e67c856a982a7b945a449b46d5bb3eab197fb8f4e8b57ecf347d40a53161a`. | This is historical step5c evidence, not a W5 result for step5d or H1-016. It does not establish all-W5 pass. |
| Official CI / PR | Upstream hosted pipeline and publication | Not run / not submitted. | No official CI, upload, push, or PR result is claimed. |

### Global W5 finding and scope

The global completeness checker returned RC=1 and that result remains unchanged. A separate review of the cited c611 baseline KV entries found multiline block content under the fields: E219 `root_cause` (5 indented content lines), E253 `root_cause` (10), E305 `root_cause` (4), and E305 `rec_approach` (17). The c611 checker examines lines individually and treats the block-scalar `|` line as empty instead of evaluating the following indented body. This is a pre-existing whole-graph checker/format conflict in c611, unrelated to the xjobs candidate; the global result is historical step5c evidence and was not rerun for step5d. The finding is disclosed; this report does not change the knowledge graph or checker, override the RC, or claim an official exemption.

### Publicly reviewable output excerpt

The following excerpt is transcribed from the formal c611 stage outputs; the consumer count is taken from its emitted result JSON. A redacted public transcript with selected original stdout/stderr, stage RCs, timestamps, and marker state is included at [step5c-w3-w5-evidence.md](step5c-w3-w5-evidence.md):

```text
检查模式: prdiff (15 个文件)
JC_RESULT=pass
JC_ERRORS=0
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: xjobs --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
test_package result JSON: passed=8, failed=0
```

The global W5 output reports the four fields listed above, while candidate-gap W5 reports `notes.md: total=0 extracted=0 pending=0 failed=0`, `manifest.yaml: knowledge_count=4 unreferenced=0`, and `知识完整性检查通过`. The linked public transcript exposes these selected primary outputs with private device paths/identifiers redacted. The complete original raw archive remains retained separately; its SHA-256 is recorded in the result table.

### Impact of the historical randomized test result

`runtest1.sh` supplies ten pseudo-random values in `[0, 10)` to `testdummy`; the helper returns 1 for values at or below 4 and 0 otherwise. The recorded three failed jobs explain the observed RC=2 under the failure-propagation behavior being corrected. That run is a genuine historical failure and remains visible; because its inputs are randomized, it is not a stable deterministic regression suite and must not be rerolled or relabeled as passing. The candidate's deterministic consumer suite separately checks parent failure propagation and that `-e` stops queued work (among its 8/8 checks), so the historical sample does not demonstrate a failure of the new deterministic checks. It also does not establish that every upstream workload succeeds.

## Other gates and limitations

- H1-014 original c611 G0 clean-build configure failed at `getcwd` (RC=1); this is a historical nonblocking G0 failure, separate from its W3 stopping at unrelated baseline markers. A later runner-only `PWD` diagnostic used a modified private runner and is not original c611 G0 evidence. Original c611 G0 was not run for step5d/H1-016.
- H1-017 ran only `FinishPipeline.step35_local_ci()` once and generated `.ci-result.json` through the official writer; it did not run full `finish`, original step5d G0, global W5, randomized upstream `make test`, or official hosted CI.
- H1-013 Toybox 0.8.12 dry-run for patch 0004 passed RC=0. The older #011-context attempt failed; the successful run applies to the later narrowed patch context.
- The full c611 global W5 RC=1 remains a recorded finding even though the candidate-only gap check returned 0.
- The current candidate status is recorded in `reports/audit-result.json`; that generated audit result is excluded from its own 16-file audit input. H1-017 W3 passed on the fixed pre-disclosure ZIP; only documentation and audit metadata changed afterward, as disclosed above.

## Reproducibility pointers

The fixed request, original tested ZIP and sidecar, stage RC files, W3 log, W5 outputs, generated marker, exact c611 checker scripts, and relevant KV entries are preserved in the local H1 evidence archive identified above. The candidate's recipe, four patches, manifest, notes, consumer recipe, and deterministic functional test are all visible in the PR diff; the W3/W5 result summary and raw-log digests in this file provide reviewer-facing traceability.

## 2026-09-29 packaging-rule and audit update

H1-017 exercised the fixed LF step5d ZIP `27e5f6c68a4edefa918fed25bedba4c4c78e4549118f94eef6afb4f2e0eee134` through official W3 once: RC=0, Conan create succeeded, `test_package` passed 8/8, and the framework writer generated a valid `.ci-result.json` whose log SHA matched. The full H1 evidence archive SHA-256 is `dfdd0342f9d9191240e87be545797fb63dbf7bee53654ab178f6263a43d1f058`. This evidence predates only the final disclosure edits to `notes.md`, this report and `audit-result.json`; no build-affecting payload changed. H1-016 remains historical for its CRLF input. H1-014 and step5c results remain historical for their inputs. No randomized upstream `make test` was included. Full `finish`, original step5d G0, and official hosted CI remain unverified.


## 2026-10-02 patch 0005 affected validation: H1-019

The latest result is scoped to tested ZIP `8908346109acf57f05c0f919c55075be7f63e994a76457fdd1f6a264c633ca54`, source `985666fede9346abe034a0074d8ab03f19f518802eaa744dd339c4028e639f38`, patch 0005 `b30bd1624ada50a035779e6976b147061c1cc237a4599790bfce8a58669bee1e`, and private profile `d311f0d72d0b81a1e7f875bcd4ef1957ac0db97c38df135566eddceb508ff3af`. The original profile `7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793` was retained unchanged. Only CONFIG_SHELL and SHELL in a private copy were changed to `/system/bin/sh`.

| Stage | Actual result |
|---|---|
| H1-018, explicit HNP Bash | getcwd/pwd Permission denied, RC=1 before patch/consumer; cause unknown |
| H1-019, existing normal sh | same ROOT/UID/GID/domain/0700/labels; access precondition RC=0 |
| Successful temporary directory | RC=0; directory 0700, subs1.awk 0600, same owner; write/append/read and owned-directory cleanup verified |
| Pre-existing directory collision | expected RC=1, File exists; sentinel and directory preserved |
| One forced-source Conan create | RC=0; configure, make -j1, package and original consumer completed |
| Original deterministic consumer | 8/8, failed=0; no added consumer assertions |
| Complete W3/finish or official CI for new inputs | not run/not established by H1-019 |

Actual command (ROOT is the unchanged H1-018 private root; PROFILE is ROOT/profiles/ohos-aarch64-normal-sh-019):

```sh
conan create "$ROOT/archives/x/xjobs/20241010" -pr:h "$PROFILE" -pr:b "$PROFILE" --build="xjobs/*"
```

Conan 2.29.1 ran in the existing isolated HOME/TMPDIR/CONAN_HOME with UID/GID 20020084, through the existing normal HiShell execution chain. New buildenv exported both shell variables as `/system/bin/sh`; new config.status started with `#! /system/bin/sh`. Buildenv SHA `9d5faf2c878b87a2cc674d52af7499961d2f08077e6c36f8629aa373440e0aac`; config.status SHA `545baac8371ad563489affeaf2499999748728980b9c5a73ef584282336884af`.

Package: `xjobs/20241010#60a66297eb60013dfc288b77ce9b664b:6b129b068851896169fae42d399fa922d239ce8a#fb9caf4236ef575d6896d23ce415b72f`. Binary: ELF64 AArch64, 84,416 bytes, actual private-package mode 0700, SHA `b11d822a7fc64ee4e8eede621ee74d8dd825a42250a3c8aace276be573a5de01`. This private execution result does not verify external package permission policy. Consumer summary SHA `449f955d2fbb50dd4c6cc9949c29fb97db56e6168c3e424844808541a1277d05`.

Request SHA `ea321a16f8ffe429c527f86dc90e779a00476853ee73f8938209e9f5e0731be8`; H1 RESULT SHA `2676b8ffa89069de597a5b6fc2c2feec4fd3217dde836f16b958a82c8712e387`; raw evidence archive (58 files, 57 manifest payloads verified) SHA `36b44511aa9bf91e83c937fb721659d066efa05298fa10667638bef8ac2650b5`. A first collection-only check incorrectly expected `#!/system/bin/sh` and returned RC=1; subsequent exact-byte shebang collection returned RC=0. Software was not rerun or changed to correct the collector. Both records and all stage stdout/stderr/RC files are preserved.

The 0005 affected source review SHA is `76ec131b363305dc427a7cf92a74ae97e3d2af39792aa3c2e9be0e2c8e3fda26`; two-line profile review SHA is `190666b747847a8063f26aa3840da671521d0d3474efd4abffd65cf1df8a8f02`. Both report static P0=0/discovered P1=0; original W4 and generated audit-result.json are historical, not regenerated pass records for patch 0005. After H1-019 only these evidence disclosures changed. Hosted CI internal76967/#66262 on old head b71aab33873bae5ac33188f4f85ed30f87ac3a21 failed in config.status first-write handling; the public candidate retains the shared official profile unchanged, so new-head official CI remains necessary. Linux build, full finish, original HNP refusal cause, formal review, merge and points are not claimed.

## H1-025 exact recorded output

Command: `/system/bin/sh -c "make test"`, cwd the H1-021 new build. Raw stdout follows; no reconstruction or rerun.

```text
./runtest1.sh
### started job #1, pid 26897: ./testdummy 9.24046
*** 0 queued, 0 finished, 0 failed, 1 running
### started job #2, pid 26898: ./testdummy 5.93909
*** 0 queued, 0 finished, 0 failed, 2 running
### started job #3, pid 26899: ./testdummy 3.06394
*** 0 queued, 0 finished, 0 failed, 3 running
### started job #4, pid 26900: ./testdummy 5.78941
*** 0 queued, 0 finished, 0 failed, 4 running
### started job #5, pid 26901: ./testdummy 7.40133
*** 0 queued, 0 finished, 0 failed, 5 running
### started job #6, pid 26902: ./testdummy 7.86926
*** 0 queued, 0 finished, 0 failed, 6 running
### started job #7, pid 26903: ./testdummy 4.3637
*** 0 queued, 0 finished, 0 failed, 7 running
### started job #8, pid 26904: ./testdummy 3.32195
*** 0 queued, 0 finished, 0 failed, 8 running
*** 1 queued, 0 finished, 0 failed, 8 running
*** 2 queued, 0 finished, 0 failed, 8 running
./testdummy 3.06394
3.06394
*** 2 queued, 1 finished, 1 failed, 7 running
### started job #9, pid 26948: ./testdummy 7.7888
*** 1 queued, 1 finished, 1 failed, 8 running
./testdummy 3.32195
3.32195
*** 1 queued, 2 finished, 2 failed, 7 running
### started job #10, pid 26955: ./testdummy 1.00887
*** 0 queued, 2 finished, 2 failed, 8 running
./testdummy 4.3637
*** 0 queued, 3 finished, 2 failed, 7 running
./testdummy 1.00887
1.00887
*** 0 queued, 4 finished, 3 failed, 6 running
./testdummy 5.78941
*** 0 queued, 5 finished, 3 failed, 5 running
./testdummy 5.93909
*** 0 queued, 6 finished, 3 failed, 4 running
./testdummy 7.40133
*** 0 queued, 7 finished, 3 failed, 3 running
./testdummy 7.86926
*** 0 queued, 8 finished, 3 failed, 2 running
./testdummy 9.24046
*** 0 queued, 9 finished, 3 failed, 1 running
./testdummy 7.7888
*** 0 queued, 10 finished, 3 failed, 0 running
```

Raw stderr:

```text
summary: 3 failed, 7 succeeded, executed in 11.17s
```

Real gawk ten-value stdout (78B, SHA256 `9d135dfc6990bc11012fe7596542bd9cacf38622d412ee4a2a7d23117cf1c1a9`):

```text
9.24046
5.93909
3.06394
5.78941
7.40133
7.86926
4.3637
3.32195
7.7888
1.00887
```
