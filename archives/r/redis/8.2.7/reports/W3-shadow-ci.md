# Redis 8.2.7 W3 shadow CI report

Date: 2026-08-16

## Result

Result: PASS on HarmonyOS 6.0/armv8 with Conan 2.29.1 and Clang 15.0.4.

The final isolated single-package run rebuilt Redis from the verified source,
restored the independently adapted Tcl build requirement, signed the target
commands before testing, ran all four official upstream entry points, packaged
the same signed binaries, and passed the 121-assertion `test_package`.

## Final input

- Commit: `de15e2c3afa3f1f91a76ca0e411dda9f0b048cb3`
- Package: `archives/r/redis/8.2.7`
- Shadow git archive SHA256: `ef9271b1701c408595664bdc155f35f664de00f558bf29db1eb56c76de82ec15`
- Source SHA256: `4b5b129565569a1564cf0196e17deff23298980e81deced3266cda58180d6506`
- Tcl cache SHA256: `3b742a313f08c8081898f419f97fa75cd8693c1d5e1c06056b9d95fb93972afe`
- Recipe SHA256: `ee213a7d8fad1b4cdff9d8e9156e1260178b1b1ca40d00602ce1fc8c40a631b3`
- Setup script SHA256: `d93c97005abe8e5c3cc8bd1076815b3a34654a523fc8c4dc8a2415a68e8367b7`
- Build script SHA256: `7983470376f3dd18f971a4cd6212ea9784ebb5245f2e833d1d67f23fa279ac31`
- Profile SHA256: `63085cfa7a03f55f2c490939df0f924a73e08005ca77db1bd851ce2c2e08d18e`

## Run evidence

- Run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/de15e2c3afa3-20260816T093310Z-redis-tcl-run-4598`
- Completed at: `2026-08-16T10:07:45Z`
- Setup return code: 0
- Dependency restore return code: 0
- Build return code: 0
- Isolation log SHA256: `cd629418d5f82d9c8ed474bddc5aa4a21cc1e40a8ee68909f367e86126ce247e`
- Setup log SHA256: `2896605956d1d5d3764531fa3cf04e4213da956e9858bdf36386988add7f955f`
- Restore log SHA256: `1b01e5a677b1150f2c6cc3f26b57c6ebe275be71b382ae983e80f60edf50e5ed`
- Build wrapper log SHA256: `2d3c9f30eee1dbff71c000336b42dc4ff0f8fc5a4184f0cac838e3638d22c259`
- Conan package log SHA256: `e9a9863d5db13c8ee0f86ceffd069c95270b2d9eb863351bd8905e8964353ff0`
- Gate results SHA256: `cba6913d5b95fbe01071cd87b768460f24c3bde4251a7cd3e4365198346a8939`
- CI metadata SHA256: `19331012c6924aef7bc0ccb4911856bd51b20915bdaf8ff325ed6ce339e54bf0`
- Conan package: `redis/8.2.7#b10fc4633aba8cb6d338ae9061bfa72f:6b129b068851896169fae42d399fa922d239ce8a#9b28b54fc9ae1e9536972203b69c31bd`

## Gate results

- L0: pass, all quality checks passed.
- L1: pass, all upstream entry points and `test_package` executed.
- L2: pass for all six packaged commands.
- L4: pass, patch scan clean.
- L5: pass, packaged `bin/` contains artifacts.
- R38 command metadata: pass; `commands.json` registers `8.2.7` as
  `redis/8.2.7`.
- R40 branch policy: warning only for PR #5315 under the current <=6000 rule.
- Destructive negative gate: pass; removing `bin/` makes the test fail.
- Build summary: 1 succeeded, 0 failed, 100 percent.

## Upstream test accounting

The source inventory contains 212 Tcl files, including harness and support
files. Test results are counted from the official runner output, not by treating
every source file as one assertion.

| Official entry point | Runner units/files | OK records | Explicit skips | Errors | Result |
|---|---:|---:|---:|---:|---|
| `sh ./runtest` | 102 units | 3,697 | 49 | 0 | PASS |
| `sh ./runtest-moduleapi` | 44 units | 534 | 6 | 0 | PASS |
| `sh ./runtest-sentinel` | 16 files | 197 | 1 | 0 | PASS |
| `sh ./runtest-cluster` | 28 files | 549 | 0 | 0 | PASS |
| **Total** | **190 runner units/files** | **4,977** | **56** | **0** | **PASS** |

Every skip is named in the log and requires real `SIGSTOP`/`SIGCONT` process
suspension. The HarmonyOS user session acknowledges `SIGSTOP` but does not
suspend the target process. The harness therefore counts only those cases as
not applicable and fails if an unaccounted pause helper is reached. Exact names
and replacement coverage are recorded in `upstream-tests.md`.

## Package test coverage

The signed package passed 121 assertions covering command presence and version,
core data structures, transactions, Lua and functions, ACLs, expiry, blocking
operations, pub/sub, output-buffer hard-limit eviction, RDB/AOF persistence and
corruption rejection, replication, WAIT/WAITAOF success and timeout, controlled
FAILOVER in both directions, minimum-replica write protection, real Sentinel
promotion, Cluster failure/recovery, benchmark load, and invalid-input paths.

These scenarios provide executable alternatives for the main functional areas
behind the pause-dependent skips. They do not claim to reproduce kernel process
suspension timing that the target user session cannot provide.

## Log audit

- No `[err]`, exception, traceback, compile error, or failed suite is present.
- `llvm-ar: warning: creating libfast_float.a` is the expected first creation of
  a static archive, not a compiler diagnostic.
- The two `RM_ReplyWithError` lines are successful Module API tests of an error
  reply, not failures.
- The device lock was released and no Redis or Tcl process remained after the
  final run.

## Failure convergence

1. The initial review follow-up added all official entry points and expanded
   `test_package` from a small smoke test to 121 assertions.
2. Signed source-tree binaries were preserved through packaging so tests and
   consumers exercise the same ELF files.
3. Process-pause-dependent tests were explicitly counted; unaccounted helper
   calls fail instead of silently succeeding.
4. Module cluster setup tests were restored after an over-broad skip exposed a
   stale Tcl handle.
5. Sentinel and standalone Cluster use a separate sequential harness, so the
   same explicit skip accounting was added there.
6. Run `0dc60e756170-20260815T091146Z-redis-tcl-run-34338` found an exact-line
   `patch_ng` mismatch. The hunk was corrected and all 10 patches then applied
   with `fuzz=False`.
7. Run `4d2d1ea20296-20260815T092251Z-redis-tcl-run-38650` passed all runtime
   tests but exposed an L4 false positive: `gets` matched the suffix of the word
   `targets` in a comment. Rewording the comment produced the final all-pass run.

## Dependency and infrastructure boundary

Tcl is test-only and remains a separate adaptation. Its recipe was merged by PR
#5327; the Redis branch contains no Tcl recipe changes and the final Shadow run
restored a checksum-verified Tcl cache. The generated `ci-metadata.json` has the
correct source SHA and commit. Its URL field is empty because the shared CI
rewrites the scalar GitHub URL to a list before a scalar-only metadata parser
runs; changing shared CI is outside this single-library PR.
