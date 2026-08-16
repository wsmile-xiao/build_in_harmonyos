# Redis 8.2.7 HarmonyOS adaptation notes

## Scope

- Issue: 2144
- Branch: `feat/redis-8.2.7-2144`
- Build system: raw Makefile (`Makefile`, `src/Makefile`, `deps/Makefile`)
- Status: built; final isolated HarmonyOS Shadow CI passed

## Source and dependencies

- Source: `https://github.com/redis/redis/archive/refs/tags/8.2.7.tar.gz`
- Tag object: `7f710225e90461d791703e36896972023ee93ed8`
- SHA256: `4b5b129565569a1564cf0196e17deff23298980e81deced3266cda58180d6506`
- Runtime Conan dependencies: none
- Vendored dependencies: hiredis, Lua, hdr_histogram, fpconv, fast_float, and linenoise
- Disabled optional features: jemalloc (`MALLOC=libc`), systemd, and TLS
- Test-only build requirement: `tcl/8.6.16`, adapted separately and not included in this PR

## HarmonyOS changes

1. Use implicit static zero initialization for the atomic callback pointer.
2. Guard glibc-only process-name globals by libc capability.
3. Provide non-glibc pthread cancellation fallbacks. `pthread_cancel` returns
   `ENOSYS`, because reporting success without cancellation can make Redis join
   a thread that is still running.
4. Invoke release and test launcher scripts through `sh` on HarmonyFS.
5. Resolve compiler tools from Conan and use `/system/bin/install` on OHOS.
6. Redirect upstream test state to the executable user-cache filesystem.
7. Sign source-tree target commands before tests and package those same files.
8. Package all six commands as regular files because package symlinks fail on
   the target filesystem.
9. Count only tests that require unavailable process suspension as explicit
   skips; fail if an unaccounted pause helper is reached.
10. Add defensive returns after assertions that compile out in release mode.

## Test strategy and result

The source inventory contains 212 Tcl files. All four official entry points run
serially against signed target binaries:

- default: 102 runner units, 3,697 OK, 49 capability skips, 0 errors;
- Module API: 44 units, 534 OK, 6 capability skips, 0 errors;
- Sentinel: 16 files, 197 OK, 1 capability skip, 0 errors;
- standalone Cluster: 28 files, 549 OK, 0 skips, 0 errors.

The 56 skips all require real SIGSTOP/SIGCONT suspension, which the HarmonyOS
user session does not provide. The 121-assertion package test adds replacement
coverage for output-buffer eviction, WAIT/WAITAOF, controlled FAILOVER,
minimum-replica policy, Cluster outage/recovery, real Sentinel promotion,
persistence, corruption rejection, replication continuity, and core commands.

See `reports/upstream-tests.md` for exact accounting and `reports/W3-shadow-ci.md`
for hashes and the full evidence chain.

## Local verification

- Official source archive and SHA256 verified.
- Python recipes compiled and YAML parsed.
- `test_package/test.sh` passed Bash syntax and LF/no-BOM checks.
- All 10 patches applied in order with Conan's `patch_ng` and `fuzz=False`.
- The CI L4-equivalent dangerous-function scan is clean.
- Local Conan inspect/export/source/graph/install preflight completed in an
  isolated task environment; the Windows host has no native OHOS toolchain.

## Final Shadow evidence

- Commit: `de15e2c3afa3f1f91a76ca0e411dda9f0b048cb3`
- Run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/de15e2c3afa3-20260816T093310Z-redis-tcl-run-4598`
- Result: setup 0, dependency restore 0, build 0
- Gates: L0, L1, L2, L4, and L5 all pass
- Package test: 121/121 assertions
- Build summary: 1/1 packages passed
- Cleanup: device lock released; no Redis or Tcl process remained

## Path B candidate

This remains a path A adaptation plus a path B knowledge-extension candidate.
The reusable contributions are the cancellation fallback semantics, HarmonyFS
script/tool/symlink handling, signed upstream-suite workflow, and explicit
capability-based test accounting. See `reports/path-B-candidate.md`.

## Reproduction

```sh
CI_PACKAGES="archives/r/redis/8.2.7" zsh ci/conan/build_and_test.sh
```

Use an isolated `CONAN_HOME`, target-local `TMPDIR`/`TMPPREFIX`, the OHOS profile,
signing tools, and a published or checksum-verified `tcl/8.6.16` package.
