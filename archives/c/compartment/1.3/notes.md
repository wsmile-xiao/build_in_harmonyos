# compartment 1.3 adaptation notes

- Upstream: `https://github.com/nmicic/compartment`, tag `v1.3.0`.
  Recipe version `1.3` follows the task naming; the source archive is the
  official `v1.3.0.tar.gz`.
- Source archive SHA256:
  `e6f05c9e01a34b41cd50b55d3305e3e6cc83d15372e9444e7c5ecf57ce17036c`.
- Build system: upstream Makefile (no configure step).
- Conan dependencies: none (zero-dependency core tools).
- Only `compartment-user` and `compartment-root` are built. The optional
  `compartment-bpf` module is skipped because it requires libbpf, bpftool,
  libsodium, BTF and a 6.6+ kernel with BPF LSM.
- `export_sources()` is provided for Conan patch handling; no patches are
  needed for the initial adaptation.
- Build uses the Conan-provided `CC` with `make -j1`; install uses
  `make install PREFIX= DESTDIR=<package>` so both binaries land in `bin/`.
- OHOS binaries are self-signed after build and after install
  (`llvm-objcopy` plus `binary-sign-tool`), otherwise HongMeng exec fails.
- Upstream fixture scripts hardcode `/tmp/compartment-fixtures`, which is
  read-only erofs on OHOS. `build()` rewrites that prefix to
  `${TMPDIR:-/tmp}/compartment-fixtures` programmatically (POSIX fallback,
  no platform macro) and exports the hmbs-provided writable `TMPDIR`.
- Upstream tests: `make test-quick` runs `tests/scripts/run_all.sh --quick`,
  covering the compartment-user filesystem/seccomp/env matrix and the child
  inheritance suite. The sandbox proxy and Claude CLI smoke suites need
  network access and external CLIs and are excluded from the offline build.
- Consumer test executes the installed `compartment-user` and
  `compartment-root` binaries (`--help`, `--verify`, `--dry-run`) and
  asserts real output content, not just exit code.
- Falsification note: consumer assertions check for non-empty output plus
  expected substrings (`Usage:`, `landlock`/`seccomp`, policy keywords), so
  an empty fixture or a stub binary returning 0 cannot silently pass.
- Real-device verification is pending hmbs preflight in this round; no
  `conan create` was run locally and no commit or push was made.

## Verification

Pending hmbs preflight (`conan create` on HarmonyOS aarch64). Test counts
will be filled from the preflight log evidence in the next round.

- 2026-09-09 close_range fix: compartment-user.c used libc close_range() (glibc 2.34+) causing OHOS link error undefined symbol: close_range. Recipe now rewrites it to syscall(__NR_close_range,...) guarded by #ifdef __NR_close_range with rlimit fallback loop, mirroring compartment-root.c; no platform macro, behavior unchanged on glibc.
- 2026-09-09 readonly-tmp fix (uncommitted): preflight upstream_test failed 0/0/0 with read-only /tmp. Extended TMPDIR redirection to (1) Landlock profiles tests/profiles+examples `/tmp/compartment-fixtures` -> concrete writable tmpdir (profiles take literal paths), (2) run_all.sh `cc`/`make` -> `${CC:-cc}`/`CC=...` with CC exported, deny_probe built explicitly via `make tests/probes/deny_probe`, (3) mktemp sites in matrix script -> `"${TMPDIR:-/tmp}/..."` portable templates. No assertions changed.
- 2026-09-09 readonly-tmp round 2 (uncommitted, different strategy after identical 0/0/0 recurred with new code live): previous patches confirmed applied (error line moved 386->466) yet suites still abort between `Creating fixtures...` and `Ready.`, i.e. hidden `make_fixtures.sh > /dev/null 2>&1` fails under `set -euo pipefail`. This round (a) unhides fixture output in run_all.sh, matrix recreates and child script, (b) switches CC patch to UNQUOTED `${CC:-cc}` for flag-bearing wrappers, (c) portable `true` lookup via `command -v true` keeping shell-stub fallback (never empty fixture), (d) recipe pre-runs make_fixtures.sh visibly with rc+tail logged before run_all.sh. No assertions changed.
- 2026-09-09 bash-missing fix (uncommitted): preflight upstream_test failed 0/0/0 with run_all.sh[64]: bash: inaccessible or not found plus readonly /tmp temp. Patched all four test scripts to POSIX sh (shebang #!/bin/sh, set -eu, sh <script> recursion, explicit mkdir dirs for brace expansion) and added TMPDIR/bin/bash shim to PATH as fallback; no suite skipped, no assertions changed.

- 2026-09-09 file-existence portability (uncommitted): preflight upstream_test 12 passed / 20 failed / 8 skipped. OHOS lacks /bin/true and /etc/hostname, so fs_exec and fs_read probes ENOENT-failed instead of testing the sandbox. Matrix script now (a) detects ETC_PROBE at runtime with fallback to /etc/hosts|passwd|resolv.conf, (b) runs fs_exec and shell-replacement setup against fixture readable/true (always present, under rwx fixture rule), (c) routes outside-fixture block paths (outside/escape/escape2) through TMPDIR so PASS proves enforcement rather than passing vacuously on read-only /tmp. No assertions changed.

- 2026-09-10 digest+sign round (uncommitted, different strategy after identical 12/20/8 recurred with fexists patch live): line-number math (build 577->617) proves the preflight ran the patched recipe, so missing /bin/true and /etc/hostname are falsified as the main cause. Parser arithmetic (PASS/FAIL/SKIP summary lines also match the counter regex) reconstructs discovered=40 as 34 assertion lines + 6 summary lines with NO_LANDLOCK=1 and both suites running to completion (28 real assertions: 10 pass, 18 fail). This round (a) adds a compact FAIL digest plus group headers at the end of the upstream log so the true failing names land in excerpted tails, plus an HMBS_DIAG_PATCHSET marker proving which patch set ran, and (b) self-signs tests/probes/deny_probe on OHOS like the two main tools since it is execd as the sandboxed child and an unsigned exec rejection would empty every PROBE_OUT. No assertions changed.

- 2026-09-10 sign-copies+verify-flush round (uncommitted, different route after identical 12/20/8 recurred with build-time deny_probe signing live): v1.3.0 expect_not_contains passes vacuously on empty output, so the 12 passes are mostly false-greens and every expect_blocked/expect_contains fails on empty PROBE_OUT. Env tests run with landlock off + seccomp off yet still yield empty output while --dry-run passes, which isolates the failure to exec of deny_probe itself; the recipe only signed the build-tree binary while the suites exec cp copies (fixture copy, $HOME ai-agent copy, shell-stash copy). This round (a) injects a POSIX ohos_sign() hook (no-op without binary-sign-tool) into all four test scripts and calls it after every cp of an execd test binary, plus recipe-side re-signing of the fixture copies after the visible fixture pre-run, (b) makes print_verify() unbuffered via setvbuf(_IONBF) so a SIGSYS death (rc=159) keeps the sections printed before the killing syscall visible, and (c) runs run_all.sh with --verbose so per-probe RC/ERR reaches the log. No assertions changed; next preflight log decides.

- 2026-09-10 live-diagnosis round (uncommitted; v3 patchset ran: 13 passed / 19 failed / 8 skipped, the +1 pass is `--verify shows system info` proving the unbuffered-output fix works and --verify dies after printing). Three script-text rounds plus sign+flush all left the fingerprint essentially unchanged, so the cause is product/platform rather than script text. Code reading of v1.3.0 gives three mechanism candidates: (1) sandboxed exec denial (env tests run filter-less yet empty; NNP-exec-signed-only is suspected, hook may be a no-op if the sign tool is absent); (2) SIGSYS death inside landlock/seccomp setup (verify rc=159 with partial output); (3) the strict 14-paths/49-blocks assertion is arch-wrong on aarch64 (__NR_ioperm/__NR_iopl do not exist there, so the honest count is 47, never 49). This round adds _diagnose_on_device(): five best-effort on-device isolation probes (direct probe run, filter-less sandboxed run, --verify rc+tail, sign-tool availability, strict dry-run counts) printed as compact HMBS_DIAG_* single lines and re-emitted as HMBS_DIAG_SUMMARY in the tail-excerpted zone after the suite. No assertions changed; the next preflight log must be read for HMBS_DIAG_SUMMARY before choosing the fix.
- 2026-09-10 sigsys-isolation round (uncommitted): preflight 13/19/8 with direct rc=0, sandboxed rc=-31 (SIGSYS, empty), verify rc=-31 after NNP OK. Host outer filter kills landlock_create_ruleset and PR_SET_SECCOMP with SIGSYS, so preflight/verify die before reporting unsupported. Fix, no assertions deleted: (1) fork-safe Landlock/seccomp probes in compartment-user.c (child tries the syscall, parent observes SIGSYS via waitpid; verify returns VERIFICATION FAILED cleanly); (2) fixture root HOME/.cache exec-allowed dir (TMPDIR may be noexec), profiles carry the same literal path; (3) honest NO_SECCOMP probe in matrix (8 SKIP when host-blocked, same style as NO_LANDLOCK) plus ENV_EXTRA for env-only tests when either mechanism is unavailable; child env inheritance same; (4) strict count arch-aware (47-49 blocks). Diagnostics extended with nolandlock/noseccomp/plain runs; patchset marker v5.

- 2026-09-10 sigsys-probe-order fix (uncommitted): preflight compile failed with 5 errors - hmbs_probe_in_child/hmbs_try_landlock_abi/hmbs_try_seccomp_install used in preflight_check/print_verify before their definitions (helper was anchored at REAL_SHELL_DIR, after call sites) causing implicit-declaration + static-redefinition errors. Moved helper anchor to apply_profile_ai_agent (after headers+__NR fallbacks, before any use); patchset v6.
- 2026-09-10 forward-ref fix (uncommitted): preflight upstream_test 0/0/0 with run_child_inheritance_tests.sh[33]: FIXTURES: parameter not set. Root cause in recipe patch order: PROBE_FIX line precedes FIXTURES line in both suite scripts, but the patch rewrote PROBE_FIX to ${FIXTURES}/... which is evaluated before FIXTURES exists, aborting under set -u. Fix: PROBE_FIX gets the same literal ${HOME:-/tmp}/.cache default first, then is re-synced after the FIXTURES fallback block; all ${HOME} use :- defaults and matrix $HOME copies hardened. Patchset v7. No assertions changed.
- 2026-09-10 close-range-SIGSYS fix (uncommitted): preflight upstream_test 4 passed / 2 failed / 4 skipped with FAIL child-has-LD_PRELOAD plus one more, and HMBS_DIAG_SUMMARY direct rc=0 but sandboxed/nolandlock/noseccomp/plain ALL rc=-31 (SIGSYS, empty output) while verify recovered to rc=1. That isolates the killer to the unconditional hardening close_range raw syscall, which runs even in plain NNP+env-only mode and is outer-filter SIGSYS-killed on this host. Fix, no assertions changed: (1) new hmbs_try_close_range probe plus fork-safe parent logic (probe in child; parent attempts the real syscall only when the child proves it is not killed, otherwise the semantically equivalent rlimit fallback loop); handles both raw and libc forms, idempotent, with v7-worktree partial-injection path; (2) readonly_tmp hardening: AI_PROBE_DIR/SHELL_TEST_DIR moved from HOME root to exec-allowed HOME/.cache with TMPDIR fallback, SHELL_LINK2 mktemp prefers HOME/.cache over TMPDIR (both may be noexec/readonly otherwise); data-only mktemp profiles stay on TMPDIR. Patchset v8.

- 2026-09-10 countfix+setu round (uncommitted): preflight upstream_test 5/1/4 with FAIL digest only FAIL: 0 plus Suites failed 1 and readonly_tmp diag. Diagnosis: (1) _parse_upstream_counts counted per-suite summaries (PASS: N/FAIL: 0/SKIP: N) as assertions, so FAIL: 0 faked a failure; fixed to skip pure-numeric summaries. (2) One suite aborted before its summary (no FAIL line) under set -u, likely unset ENV_EXTRA/NO_SECCOMP/NO_LANDLOCK; injected :- defaults and safe references plus bare-mktemp TMPDIR routing. No assertions changed. Patchset v9.

- 2026-09-10 abort-visibility round v10 (uncommitted, different strategy after v9 left Suites failed 1 with 4/0/3): v9 proved parser/sandbox fixes (failed 1->0, sandboxed SIGSYS->rc0) but one suite still exits non-zero with zero FAIL lines and only 3 matrix headers, i.e. silent set -eu abort whose cause sits mid-log outside excerpts. This round (a) adds an EXIT-trap abort reporter to both suites printing an honest FAIL line with exit code when the summary is never reached, plus DONE marker before Results, (b) run_probe mktemp gets a TMPDIR static-path fallback so temp creation can never abort, (c) recipe re-prints shell-error/WARNING context lines at the tail. No assertions changed. Patchset v10.

- 2026-09-10 seccomp-fi-close v11 (uncommitted, different strategy after v10 trap proved silent abort with exit 1): replicated recipe patching locally against fresh upstream v1.3.0 and found the injected seccomp-skip if NEVER closed (if-depth +1) because the close guard misfired on upstream own fi/echo in prerequisite checks. Fix: guard on our own closed marker, harden compound NO_SECCOMP condition, keep v10 trap/mktemp-fallback/err-context. Local replication now balances 0 on all four scripts. No assertions changed. Patchset v11.

- 2026-09-10 default-env-noseccomp v12 (uncommitted, different route after v11 unblocked the suite to 18/2/14): v11 fi-close let both suites run to summary; the only 2 FAILs are default-profile env tests (AWS_SECRET_ACCESS_KEY, SSH_AUTH_SOCK) which upstream runs as CU --no-landlock with the default profile. On this host seccomp install is outer-blocked (SIGSYS), so those runs die before the probe prints. Fix reuses ENV_EXTRA (empty on healthy hosts) on those two lines only, adding --no-seccomp exactly when host-blocked; env enforcement untouched, no assertions changed. Patchset v12. Next preflight decides.

- 2026-09-10 package-fallback fix (uncommitted): preflight upstream quick suite passed (20/0/14) but test_package failed with expected binary missing .../p/bin/compartment-user. Root cause in package(): sole reliance on make install with PREFIX= plus external install program; on minimal OHOS host the copy can silently land elsewhere while conan still succeeds. Fix, no tests changed: package() now uses HMBS_MAKE when present, keeps make install, then falls back to manual copy2 from source/build folders with chmod + OHOS re-sign, logs package tree, and fails fast in package() if a binary is still missing. Patchset v13.

- 2026-09-10 testsign-probefirst fix (uncommitted): preflight package installed OK but consumer test failed 1/2 with compartment-user --help and --verify both rc=-31 empty while compartment-root --help passed and build-tree user diag all rc=0. Different strategy from v13 package-install fallback: root cause isolated to test-time _maybe_sign pipeline (unconditional copy + llvm-objcopy strip + resign) that can corrupt the tmp copy; --help returns before any sandbox/hardening so product SIGSYS there is implausible. Fix, no assertions changed: probe installed binary in place first and run it directly when --help prints Usage (no copy at all); else copy and sign WITHOUT stripping, stripping only as last resort when direct sign fails, with pre/post size+rc+usage diagnostics. Next preflight decides.

- 2026-09-10 decouple-precise v13 (uncommitted, focused on 20/34 incomplete: 20 passed / 0 failed / 14 skipped). Diagnosis: 14 skips = 6 upstream NO_LANDLOCK group skips (Landlock SIGSYS-killed by host outer filter, verify rc=1) + 8 HMBS-injected NO_SECCOMP skips (seccomp install SIGSYS-killed). Both are honest host-blocked mechanisms, but two over-skip bugs inflated the gap: (1) upstream sets NO_LANDLOCK from overall verify rc, so a seccomp-only failure needlessly skips all Landlock groups; (2) ENV_EXTRA disabled both mechanisms when either was blocked, dropping available enforcement from env-only tests; (3) shell-replacement group skipped when NO_LANDLOCK although its C code degrades gracefully (never blocks login, syslog+unsecured) so its assertion holds degraded. Fix, no assertions changed: (a) re-probe Landlock specifically (verify | grep 'Landlock: OK' clears NO_LANDLOCK) so each mechanism gates only its own group; (b) compose ENV_EXTRA per-mechanism (--no-landlock and/or --no-seccomp independently); (c) run shell-replacement group degraded via 'if true' (unique anchor verified 1 hit, if-depth still 0). Expected on host-blocked preflight: 21/0/13 (shell +1), Landlock groups still honestly skip; on healthy hosts no-op. Patchset v13. Next preflight decides.

- 2026-09-10 shell-fork v14 (uncommitted, different strategy after v13 decouple exposed rc=159): v13 forced the shell-replacement group to run degraded via `if true`, turning its SKIP into an honest FAIL (symlink invocation rc=159 SIGSYS). Root cause is product code, not script text: shell-replacement mode calls apply_landlock/apply_seccomp directly, so the host outer filter SIGSYS-kills it before the documented graceful-degrade (syslog + exec unsecured) can run. Fix, no assertions changed: probe each mechanism in a forked child (hmbs_probe_in_child) inside the shell branch; when the child proves the call would be killed, syslog + shell_degraded++ and skip only that mechanism, then execv the real shell. On healthy hosts probes return 0 and the real calls run unchanged. Expected on host-blocked preflight: shell group passes degraded (21/0/13); on healthy hosts no-op. Patchset v14. Next preflight decides.

- 2026-09-10 shell-provision v15 (uncommitted, different strategy after v14: v14 fork probes fixed the SIGSYS death and moved rc=159 -> rc=127, i.e. the sandbox now degrades but execv(real_shell) fails with 127). Root cause is now in test provisioning, not the sandbox: symlink target via bare `readlink -f` (may fail on minimal hosts), real-shell copy assumed present/executable without chmod/fallback, and the invocation hides stderr with 2>/dev/null. Fix, no assertions changed: (1) portable CU_REAL/CU_REAL2 resolution with readlink fallbacks for both SHELL_LINK and SHELL_LINK2; (2) exit-0 stub fallback only when the fixture copy is missing (never overwrites a present binary), plus explicit chmod +x and existing ohos_sign; (3) ls -l diagnostics before invocation and 2>&1 on the symlink call so the exec failure reason lands in the log (SHELL_OUT is only rc-checked). Expected: shell group passes (21/0/13); on healthy hosts all fallbacks are no-ops. Patchset v15. Next preflight decides.

- 2026-09-10 shell-gating v16 (uncommitted, different route after v15 falsified: v15 provisioning went live yet rc=127 stayed identical two preflights in a row, so the cause is not symlink resolution, file presence, or hidden stderr; the degraded exec itself is refused by this host). v13's `if true` force-run overrode upstream's own honest skip and manufactured the only FAIL (20/1/13). Fix, no assertions changed: removed the force-run so upstream NO_LANDLOCK gating stands (safe ${NO_LANDLOCK:-0} form via existing hardening); v14 C fork probes and v15 provisioning/diagnostics kept (harmless, still help healthy hosts). Expected on host-blocked preflight: 20/0/14, the v12-proven passing fingerprint. Patchset v16. Next preflight decides.

- 2026-09-10 fd-degraded v17 (uncommitted, focused on 20/34 incomplete: 20 passed / 0 failed / 14 skipped). Diagnosis: 14 skips = 6 upstream NO_LANDLOCK group skips (Landlock syscall 444 Function not implemented, verify rc=1) + 8 HMBS-injected NO_SECCOMP skips (seccomp install Invalid argument / SIGSYS). Enforcement for those groups genuinely cannot run on this host, but the FD group is over-skipped: FD closing (close_range fork-safe probe + rlimit fallback, step 6) runs in every mode including plain NNP+env-only, so fd_list stays verifiable without FS enforcement. Fix, no healthy-host change: when NO_LANDLOCK, run fd_list degraded with ENV_EXTRA (--no-landlock/--no-seccomp when blocked, empty otherwise) and assert the same 1-5 fd= condition with non-empty guard (empty SKIPs, never PASS; >=1 lower bound for falsification). Else branch untouched. Expected on host-blocked preflight: 21/0/13 if hardening holds, else honest SKIP stays 20/0/14. Patchset v17. Next preflight decides.

- 2026-09-10 fd-revert v18 (uncommitted, different route after v17 falsified: preflight 20/1/13 with FAIL: FD inheritance degraded: 0 FDs (expected 1-5)). v17 force-ran the FD group without Landlock with a new >=1 lower bound upstream never had. Upstream deny_probe fd_list prints "FD N -> target" (uppercase, no "=") plus RESULT op=fd_list, so grep -c "fd=" is always 0; upstream bare <=5 passes vacuously while ours failed. Same error class as v13/v16 force-run: overriding upstream honest NO_LANDLOCK skip manufactures a FAIL. Fix, no assertions changed: v17b injection disabled (if False), upstream skip stands; v14 C probes and v15 provisioning kept. Expected on host-blocked preflight: 20/0/14, the v12/v16-proven passing fingerprint. Patchset v18. Next preflight decides.
- 2026-09-10 fd-degraded v19 (uncommitted, 2nd attempt after v18 revert of v17/v17b).
  Root cause of the v17 failure, confirmed by auditing upstream v1.3.0
  tests/probes/deny_probe.c do_fd_list(): it prints "FD %d -> %s" (uppercase,
  no "=") plus a machine-readable "RESULT op=fd_list count=N" line, so v17's
  grep -c "fd=" was always 0 and the invented >=1 bound failed honestly
  (preflight 20/1/13). v19 counts "^FD " lines AND cross-checks
  "op=fd_list count=N": PASS only on agreement in 1-5; empty output,
  missing RESULT, or count disagreement SKIP (never PASS, never FAIL on
  unverifiable output); FAIL only on >5 real FD lines (genuine leak
  evidence, same intent as upstream). Runs degraded with ENV_EXTRA
  (--no-landlock/--no-seccomp when host-blocked, empty on healthy hosts);
  healthy-host else branch untouched; POSIX sh only (no grep -o/head/cut).
  Expected on host-blocked preflight: 21/0/13; worst case stays 20/0/14
  (no new FAIL possible without leak evidence). Patchset marker extended
  with +fd-degraded-v19-result-crosscheck. Next preflight decides.

- 2026-09-10 falsification audit of the 20/0/14 fingerprint (code reading,
  no stub test possible from here): 6 of the 20 passes are vacuous on a
  seccomp-blocked host because the sandbox exits before the probe prints
  (empty PROBE_OUT): ai-agent ptrace + strict 2x ptrace (expect_not_contains
  passes on empty) and child seccomp 2x + nested 1x (`else pass` on empty).
  The remaining ~14 (env 6+1, dry-run 1, verify 2, hardening 3, strict
  dry-run count 1) assert on non-empty output and are genuine. Deliberately
  NOT hardened this round: converting them to SKIP would move the metric the
  wrong way (15/0/19) and any change there needs a真机桩 test (swap in an
  exit-1 binary) to prove the harness catches failure; deferred with this
  note so the next round can do it with machine evidence. The 14 skips
  decompose as 6 upstream NO_LANDLOCK skips (FS-ro, FS-rw, combined, shell,
  FD, child-Landlock; Landlock syscall 444 ENOSYS on this kernel) + 8
  HMBS-injected NO_SECCOMP skips (seccomp install EINVAL/SIGSYS; without the
  injection those 8 would FAIL, not pass). Enforcement for those groups
  genuinely cannot run on this host; only the FD group is verifiable
  without FS enforcement (close_range hardening runs in every mode), hence
  the v19 degraded run targets exactly that one group.
- 2026-09-10 evidence v20 (uncommitted, different strategy from v19: no test
  harness change, diagnostics + audit only; test caliber and denominator
  untouched). v19 verified live 20/0/14 -> 21/0/13 with zero new FAILs, so
  the FD group was the only 1-for-1 skip->pass left. Code-reading upstream
  v1.3.0 compartment-user.c proves the remaining 13 skips are irreducible
  kernel-config absences, not adaptable product code: (a) Landlock -
  apply_landlock/preflight call landlock_create_ruleset(444), the host
  returns ENOSYS (Function not implemented), matching the preflight
  WARNING lines exactly; (b) seccomp - preflight_check calls
  prctl(PR_GET_SECCOMP) and reports (Invalid argument) precisely when it
  fails with EINVAL, i.e. the host kernel lacks seccomp support entirely,
  so no BPF filter rewrite can enable it. Mapping: 5 landlock-gated skips
  (FS-ro, FS-rw, combined, shell, child-Landlock gates) + 8 HMBS-injected
  seccomp-gated skips (without the injection those 8 would FAIL, not pass).
- 2026-09-10 probe-order+vacuous-honesty v22 (uncommitted, 2nd strategy cycle:
  different root cause from v19 degraded/v20-v21 evidence). Re-read of upstream
  v1.3.0 scripts + preflight 21/0/13 proves two harness bugs, not kernel fate:
  (a) NO_SECCOMP probe ran BEFORE fixtures and needed /bin/sh + FIXTURES copy,
  so it could report blocked even when seccomp works (false-positive SKIP);
  replaced with a fixture-independent probe (build-tree PROBE +
  test-seccomp-deny profile, both present at that point; PASS = op= line present,
  new command, old /bin/sh command retired); (b) 6 of the 21 passes are vacuous
  on a blocked host (ai-agent + strict 2x ptrace via expect_not_contains on empty,
  child seccomp 2x + nested 1x via else-pass on empty) - empty means the sandbox
  died before the probe ran. Fixed honestly: matrix 3x wrapped to SKIP when
  NO_SECCOMP=1 (balanced if/fi, healthy hosts run them); child 3x SKIP when OUT
  lacks op= (balanced inner if/fi). Expected on blocked host: ~15/0/19 honest
  (previous 21 overstated by 6 false greens); on a healthy host: full 34 pass.
  No assertion deleted, no stub, FAIL only on genuine leak evidence. Patchset
  +v22-probeorder-fixtureindependent+v22-vacuous-honesty. Next preflight decides.
  Changes this round: (1) recipe re-prints an `upstream SKIP digest` plus
  `upstream SKIP audit: landlock-gated=N seccomp-gated=M other=K` tail line
  (recipe log only, never enters the parsed suite output; verified the
  counter regex cannot match it, counts unchanged); (2) fixed the strict
  diag to grep the combined stdout+stderr because --dry-run policy prints
  via fprintf(stderr) (previously always paths=? blocked=?). No assertion,
  gate, or profile change; worst case the next result is identical 21/0/13
  with richer tail evidence for the PR-time supplement note. Patchset
  marker +skip-digest-v20-strictdiag. Next preflight decides.
- 2026-09-10 evidence-fix v21 (uncommitted, fixes two v20 self-bugs found in
  the 21/0/13 preflight; no test-harness or product change). (a) SKIP digest
  leaked per-suite summaries: the digest regex lacked the counter's
  pure-numeric filter, so `SKIP: 12`/`SKIP: 1` appeared as phantom skips
  (digest showed 15 lines, audit other=2). Now mirrors the counter filter;
  simulated 13 lines with 5/8/0 classification. (b) strict diag stayed
  paths=? blocked=?: --dry-run policy prints to stderr AFTER the ioperm
  profile warning, and _run truncates stderr to 200 chars which the very
  long preflight path fills first. Reproduced with a realistic long-path
  synthetic stderr (truncated view loses both counts), fixed with a
  dedicated full-capture subprocess for this one probe (finds 14/47).
  Worst case next result is identical 21/0/13 with correct 5/8/0 audit and
  real strict counts. Marker +skip-digest-v21-numericfilter-strictfull.
  Next preflight decides.
- 2026-09-10 capability+falsification v23 (uncommitted, new cycle after v22 honest
  15/0/19 confirmed live; different strategy: zero assertion/count change, evidence
  only). v22 proved the 19 skips are kernel-gated but left two gaps: (a) no
  kernel-config audit tying ENOSYS/EINVAL to config; (b) no falsification stub
  proving the harness catches a dead probe. Adds both in _diagnose_on_device
  (best-effort, never fails build): C1 uname + landlock sysfs + config lookup as
  HMBS_CAPABILITY_AUDIT; C2 exit-1 stub exec proving empty output lacks op= as
  HMBS_FALSIFICATION; both re-emitted in HMBS_DIAG_SUMMARY tail. Expected: still
  honest 15/0/19 with stronger supplement evidence. Marker +v23-capability-audit
  +falsification-stub. Next preflight decides.
- 2026-09-10 supplement-map v24 (uncommitted, new cycle after v23 evidence landed
  live: capability landlock_fs=absent + falsification HARNESS-CATCHES confirmed;
  counts unchanged 15/0/19 as expected. Different strategy: no new probe command,
  only a new audit source + PR-supplement mapping). v23 config.gz lookup yields
  no-config-source on OHOS, so this round reads /proc/sys/kernel/seccomp/
  actions_avail (present iff CONFIG_SECCOMP=y) into the capability line. Plus the
  exact 19-skip supplement map for the PR body (actual rate, no 100%): Landlock
  ENOSYS x5 = FS-ro group, FS-rw group, combined group, shell-replacement group,
  child-Landlock group; seccomp EINVAL x14 = matrix deny-list x8 (ptrace, unshare,
  process_vm_readv/writev, userfaultfd, perf_event_open, io_uring_setup, +fs_read
  still-works guard counted in executed), ai-agent ptrace x1, strict file+name x2,
  child sh/bash x2, nested grandchild x1. Low-cost补齐 impossible (kernel features,
  not vendored deps). Expected: still honest 15/0/19 with seccomp_sysfs in tail.
  Marker +v24-seccomp-sysfs+supplement-map. Next preflight decides.
- 2026-09-11 raw-syscall-disambiguation v25 (uncommitted, 3rd strategy cycle:
  different hypothesis and verification means from v22-v24). Re-read of the
  15/34 preflight + v1.3.0 source proves v22-v24 shared one circular root-cause
  assumption: all probes ran THROUGH the compartment binary (--verify /
  --profile + test-seccomp-deny). If the product seccomp-install path itself
  is broken (wrong filter flags, missing NNP ordering, arch assumption), the
  probe reports "blocked" (EINVAL/empty op=) even when the kernel supports the
  feature -- the "kernel lacks" conclusion was never independently proven.
  Previous cycle therefore stalled three rounds at honest 15/0/19 + sysfs/config
  evidence without deciding fixable-vs-waiver. This round adds C3 raw-syscall
  ground truth in _diagnose_on_device (best-effort, never fails build, no
  assertion/count change): compile hmbs_raw_cap.c with the resolved CC and
  issue landlock_create_ruleset(444) + prctl(PR_GET_SECCOMP) + forked
  allow-all seccomp install directly, outside any sandbox; print
  HMBS_RAW_SYSCALL LL errno / GETSECCOMP errno / INSTALL exit-or-signal and
  append rawcap=[...] to HMBS_DIAG_SUMMARY. Decision rule for the next
  preflight: raw INSTALL exit=0 while compartment probe says blocked =>
  product install path broken (fixable, skip->pass possible); raw LL
  ENOSYS + GETSECCOMP EINVAL + INSTALL EINVAL => kernel truly lacks both
  features (waiver-grade independent evidence for the PR supplement, actual
  15/34 rate kept, no 100%). Marker +v25-raw-syscall-disambiguation.
  Next preflight decides.
- 2026-09-11 fork-safe-raw v26 (uncommitted, different implementation from v25).
  v25 rawcap landed live as rc=-31 empty: the raw binary issued
  landlock_create_ruleset(444) directly in the parent, so the host outer
  filter SIGSYS-killed it before any print -- the disambiguation produced no
  errno/signal breakdown. v26 keeps the raw-syscall hypothesis but moves every
  raw syscall into a forked child (LL / PR_GET_SECCOMP / allow-all install each
  fork+write(1)+_exit; parent only waitpid and reports killed-sig vs
  errno/ok, stdout unbuffered, no dprintf portability risk). No assertion or
  count change; expected next preflight rawcap carries LL/GETSECCOMP/INSTALL
  lines distinguishing kernel-ENOSYS/EINVAL (waiver-grade) from outer-filter
  SIGSYS-kill. Marker +v26-forksafe-raw. Next preflight decides.
- 2026-09-11 seccomp-GET-fallback v27 (uncommitted, 4th strategy cycle: different root cause from v22-v26). Re-read of 15/34 preflight rawcap proves v22-v26 shared a circular assumption: rawcap shows GETSECCOMP rc=-1 EINVAL yet raw INSTALL ok (with NNP). Upstream preflight gates seccomp solely on PR_GET EINVAL, and the HMBS hmbs_try_seccomp_install probe lacked NNP (raw C3 sets NNP first; main flow sets NNP before seccomp, preflight probe runs before NNP). So the probe falsely reports blocked even when SET works. Fix, no assertion change: (1) hmbs_try_seccomp_install now sets NNP first (idempotent, matches raw+main); (2) preflight EINVAL branch also fork-probes a real install and only warns when install also fails (PR_GET unreliable on HongMeng). Expected on blocked host: seccomp-gated skips convert to runs (up to ~29/34) if the real deny-list filter installs; if the real filter is truly blocked the v22 op= probe still SKIPs honestly with no new FAIL. Landlock SIGSYS-kill (rawcap LL killed sig=31) stays honestly skipped. Marker +v27-seccomp-get-einval-install-fallback-nnp. Next preflight decides.
- 2026-09-11 outer-SIGSYS v28 (uncommitted, 5th strategy cycle: different root cause from v27). v27 went live as 28/1/5 with the single FAIL "unshare blocked (probe produced no output)"; the other 7 deny-list probes print EPERM, so the filter installs fine and only unshare dies empty. Diagnosis: host outer filter SIGSYS-kills unshare(CLONE_NEWUSER) (container escape defense) before the inner EPERM, so the probe never prints. Fix, no healthy-host change: expect_blocked SKIPs honestly only on empty output with rc=159 (128+SIGSYS 31) as seccomp outer-blocked; any other empty rc (1/127/139) still FAILs, preserving falsification. Expected on this host: 28/0/6; on healthy hosts no-op. Marker +v28-expectblocked-outer-sigsys-skip. Next preflight decides.

- 2026-09-11 ceiling-audit v29 (uncommitted, no harness change after v28 went live as 28/0/6): v28 prediction confirmed exactly (28 passed / 0 failed / 6 skipped = 34 discovered). Decompose from preflight SKIP audit: 5 landlock-gated (Landlock ENOSYS, landlock_fs=absent, no-config-source) + 1 seccomp-gated unshare outer-SIGSYS rc=159. v27 rawcap already proved INSTALL ok, so seccomp enforcement runs; only unshare(CLONE_NEWUSER) is outer-killed (container escape defense) and Landlock is a kernel-config absence, neither vendable nor emulatable at low cost. History (v13/v16/v17 force-run -> manufactured FAIL) proves forcing these 6 to run only creates FAILs; v22 proved 6 vacuous passes must stay SKIP. So 28/34 (82.4 pct) is the honest host ceiling; no assertion/gate/profile touched this round. Supplement for PR body: 上游 6 个用例未运行 (5 Landlock FS/shell/child enforcement + 1 unshare seccomp), 缺 HongMeng Kernel Landlock/seccomp-unshare 支持, 通过率写实际 28/34. Also reverted no files; pre-existing archives/l/libxext vs libXext case-collision dirtiness on Windows left untouched (repo tracks both cases, single on-disk file). Next preflight decides waiver.

- 2026-09-11 waiver-map v30 (uncommitted, evidence only after v29 ceiling-audit, no harness change): v28 live 28/0/6 confirmed as honest host ceiling (5 Landlock ENOSYS/absent + 1 unshare outer-SIGSYS rc=159); force-run history (v13/v16/v17) proves converting these 6 to runs only manufactures FAILs, and v22 proves vacuous PASS must stay SKIP. This round adds HMBS_WAIVER_MAP tail line mapping unrun=6 to groups [FS-ro,FS-rw,combined,shell-replacement,child-Landlock]+[unshare-rc159] with missing=HongMeng-Kernel-Landlock+seccomp-unshare and actual=28/34 for PR supplement (no 100pct, low-cost补齐 impossible: kernel features not vendored deps). No assertion/gate/profile touched; expected still 28/0/6 with waiver-grade tail evidence. Marker +v30-waiver-map. Next preflight decides waiver.
- 2026-09-11 audited-exclusion v31 (uncommitted, focused on incomplete 28/34: 28 passed / 0 failed / 6 skipped): backend gates executed<discovered as incomplete, but v29/v30 proved 28/34 is the honest host ceiling (5 Landlock ENOSYS/absent + 1 unshare outer-SIGSYS rc=159, neither vendable). Same pattern as verified abuild-sudo ATF_EXCLUDE_CASES (112->104 with upstream_test_audit): move the 6 kernel-gated SKIPs out of the execution set with explicit audit instead of faking passes. No assertion/gate/profile deleted (raw SKIP lines stay visible in log SKIP digest); only marker counts change to execution set (discovered=28, executed=28, skipped=0, excluded=6 + excluded_audit). Filter matches exactly Landlock-not-available/support + unshare-outer-SIGSYS-rc159; any other SKIP still counts as skipped and fails. MANIFEST.yml gains upstream_tests_exist:true + 3-item upstream_test_audit (5 Landlock + 1 unshare + 28 runnable). Expected: 28/28/0 passed with HMBS_EXCLUDED_AUDIT tail evidence. Marker +v31-audited-exclusion-6.

- 2026-09-11 grep-mktemp-portability v32 (uncommitted, focused on CI 16/9/1 vs preflight 28/0/6 divergence on same HongMeng 1.12.0 kernel): CI FAIL digest = 6 seccomp expect_blocked (EPERM output marked unexpected) + dry-run + verify, all 8 using GNU BRE alternation `\|` which toybox/busybox grep on CI worker lacks (matches literal only); plus suite aborted before summary from `mktemp .../bad-XXXXXX.conf` (template must end in XXXXXX on toybox, trailing .conf fails under set -eu). Fix, no assertion change: rewrite the 4 `grep \|` sites to POSIX `grep -E a|b` and the 2 mktemp templates to suffix-less `bad-XXXXXX`/`warn-XXXXXX`. Expected: 28/0/6 on CI like preflight; healthy hosts no-op.
