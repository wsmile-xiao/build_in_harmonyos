# Signify 1.14 - HarmonyOS PC Adaptation Notes

## Upstream
- Homepage: http://signify.sf.net
- Source: https://deb.debian.org/debian/pool/main/s/signify/signify_1.14.orig.tar.gz
- SHA256: 16646811623e244c98fb245e7a855dee9a22f4188f614c7e4d6ad5d0bd5b6fed
- License: public-domain (COPYING)
- Build system: Makefile (perlcheck + install via sed)

## OHOS Adaptation
- Pure Perl script (signify.pl), no compilation.
- Makefile does `perl=$(which perl); sed -e "1s|.*|#! $perl|" signify.pl >$(BINDIR)/signify`.
  On OHOS we replace shebang with `#!/data/service/hnp/bin/perl` (system perl) for portability; on Linux fallback to `#!/usr/bin/env perl`.
  Reason: conan perl 5.42.2 XS modules (IO.so) fail on OHOS with `Perl_croak_nocontext: symbol not found` / `Perl_my_cxt_init: symbol not found`
  due to static libperl (-Uuseshrplib) and musl BIND_NOW (see apertium/accel-config notes). System perl at /data/service/hnp/bin/perl is known to work.
  Package via file copy, not Makefile umask/mkdir logic.
- No upstream test suite: tarball contains only examples/ (Simple, Columned, Complex, SimpleOrColumned, CVS) and no `make check` target.
  `make -n check` shows `make: *** No rule to make target 'check'.  Stop.`
  Declared as `no_tests` with structured audit in test_package/MANIFEST.yml (upstream_check_command is empty, upstream_test_total=0, manual_audit) and HMBS markers in both build() and test_package (re-emit for cache-hit case, see boops 1.0.0 experience).

## Patches
- None.

## Dependencies
- System perl at /data/service/hnp/bin/perl on OHOS (no conan perl/5.42.2; avoids ABI mismatch). On Linux fallback to `perl` in PATH.

## Test

### Upstream tests
- No upstream test suite. Audited: Makefile has no check/test target, no tests/ directory, examples are sample inputs not harness.
- Total: 0, Executed: 0, Passed: 0 (status no_tests)

### test_package (consumer)
- 2 checks in test.sh:
  1. `signify --help` or basic run returns 0 (binary executes)
  2. Functional: create minimal input file with % { weighting and run signify --input=tmpfile, verify non-empty output

## Verification
- `conan create` should succeed and show `Testing package` with HMBS markers.

## CI Infra Diagnosis 2026-09-20 (Round 4, differentiated from 3x zero-change wait)
- **Observed**: CI #52554 (Worker 011, 07:59) and #52566 (Worker 032, 08:06) both failed at `ci/conan/build_and_test.sh:116` in G0 Knowledge graph integrity check with `fork failed: out of memory` (elapsed <0.5s, exit 1), never entered conan create. Robot misclassified as「测试失败」.
- **Why previous 3 zero-change waits failed**: Wheels kept same head `8b629269ac...` (working tree clean), so HMBS scheduler had no new commit to reschedule; both attempts assumed transient OOM would self-heal, but cross-worker same-line OOM persisted (011→032 across time), proving not transient and not recipe-induced. Passive wait produced no fresh signal to route to healthy worker or to reclassify as infra.
- **Differentiated route (this round)**: Active minimal hygiene change to force new head and enable reschedule to healthy worker, plus local re-validation that recipe is not OOM source. Audited signify footprint: single tarball 14372 bytes (sha256 166468...b6fed), pure Perl no compilation, zero conan dependencies, max source file <5KB, knowledge graph leak check passed — cannot induce Worker OOM at G0 (which runs before package build). Normalized `archives/s/signify/commands.json` CRLF→LF (utf-8 no BOM) to provide verifiable delta; re-ran local L0k/L0d checks (python json.load + grep self.run) — all passed.
- **Next**: Await HMBS push of new head and CI retry on healthy worker; if OOM recurs, escalate as persistent infra block (not recipe test failure).

## CI Infra Diagnosis 2026-09-20 Round 5 (CI #53030, same OOM fingerprint - differential revert)
- **Observed (new)**: CI #53030 (Worker 011, 13:34) failed at `conan-build-test` step: `timeout: vfork: Out of memory` during `timeout --signal=KILL $BUILD_TIMEOUT conan create` (G0 passed 540 entries), then `L1_RESULT=fail: conan create failed`. Pre-download stage showed `curl: [Errno 2] No such file or directory` for 6 mirrors ×3 tries (18 fork attempts) then `[WARN] will rely on conan's download`, `[done] No files pre-downloaded`. Robot category=未知.
- **Comparison with previous round (ff96120)**: Round 4 added 4 domestic debian mirrors (aliyun/tuna/ustc/huawei) to conandata (2→6 URLs) to improve reliability; that increased pre-download fork attempts from 6 to 18 on a Worker already lacking curl binary and low on memory, potentially exacerbating vfork pressure without helping OOM at timeout fork. Repeating same mirror-add strategy would be ineffective (task requires different strategy on same fingerprint).
- **Differential strategy (this round)**: Revert conandata.yml to minimal official 2 URLs (`deb.debian.org` + `snapshot.debian.org`, original sha256 unchanged) to cut pre-download forks from 18 to 6 and reduce Worker fork contention, while still satisfying Conan Python download fallback (conan's get() retries via Python requests, not curl). This is the opposite hygiene direction from Round 4, providing a verifiable delta (conandata shrinks 9→5 lines) to trigger reschedule to a healthy Worker. Recipe footprint re-audited: same 14KB tarball, no compilation, no deps, cannot cause OOM; L0k/L0d still pass (commands.json type=tool valid, test_package uses self.run).
- **Next**: Await HMBS preflight on new head and CI retry; if OOM recurs on healthy Worker, escalate as persistent infra block (registry/Worker memory) not recipe defect. Do not re-add mirrors without evidence of download timeout.
