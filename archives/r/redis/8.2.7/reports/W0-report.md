# Redis 8.2.7 W0 and preflight report

Date: 2026-08-16

## Work isolation

- Issue: 2144
- Branch: `feat/redis-8.2.7-2144`
- Worktree: `D:\harmonyos\worktrees\redis-8.2.7`
- Only `archives/r/redis/8.2.7/`, required Redis command metadata, and
  Redis-specific knowledge drafts are changed.
- The primary Apache Arrow checkout was not switched or modified.

## Dependency result

Redis has no external runtime Conan requirements for the selected minimal
configuration. Required libraries are vendored under `deps/`; the recipe uses
`MALLOC=libc`, `USE_SYSTEMD=no`, and `BUILD_TLS=no`.

The official tests require `tcl/8.6.16` as a build-only tool. Tcl is an
independent adaptation and PR, not part of the Redis change. Final Shadow
evidence restored a checksum-verified Tcl cache with SHA256
`3b742a313f08c8081898f419f97fa75cd8693c1d5e1c06056b9d95fb93972afe`.
The independent Tcl recipe was merged by PR #5327; no Tcl recipe change is
included in this Redis PR.

## Source audit

- URL: `https://github.com/redis/redis/archive/refs/tags/8.2.7.tar.gz`
- Size: 3,959,871 bytes
- SHA256: `4b5b129565569a1564cf0196e17deff23298980e81deced3266cda58180d6506`
- Tag object: `7f710225e90461d791703e36896972023ee93ed8`
- Build system: raw Makefile
- Vendored directories: fast_float, fpconv, hdr_histogram, hiredis, jemalloc,
  linenoise, and lua
- Test inventory: 212 Tcl files; 114 under `tests/unit`

## Compatibility analysis

- Glibc-only globals are guarded by libc capability rather than an OHOS macro.
- Unsupported pthread cancellation returns `ENOSYS`, preserving caller control
  flow and avoiding a join of a thread that was not cancelled.
- HarmonyFS requires explicit shell invocation for readable archived scripts.
- `/system/bin/install` is used because the user-local helper is not executable.
- OHOS package aliases are regular signed files because symlink creation fails.
- Upstream tests need signed source-tree executables and writable/executable
  state below `/data/storage/el2/base/cache`.
- Process suspension is unavailable to the user session and must be accounted
  per test, not by dropping complete suites.

## Local validation

- `conan inspect`, `conan export`, `conan source`, `conan graph info`, and
  `conan install --build=never` passed in a task-local environment.
- Source URL and SHA256 were verified.
- All 10 patches applied to a clean official source tree using the same
  `patch_ng` library as Conan, with `fuzz=False`.
- Recipe Python syntax, YAML parsing, shell syntax, LF/no-BOM, `git diff --check`,
  and the CI L4-equivalent scan passed.
- `archives/r/redis/commands.json` parses and maps `8.2.7` exactly to
  `redis/8.2.7`; the current R38 command-metadata gate passed.

The Windows host has no OHOS compiler, Make, container runtime, or WSL. Native
build and runtime validation therefore ran on the HarmonyOS Shadow device.

## Completed device entry

```text
library: redis
branch: feat/redis-8.2.7-2144
issue: 2144
package: archives/r/redis/8.2.7
resource: CPU / IO / loopback network
actual duration: 34m35s for final full run
command: CI_PACKAGES="archives/r/redis/8.2.7" zsh ci/conan/build_and_test.sh
result: PASS, L0/L1/L2/L4/L5 all pass
```

Final run:
`/storage/Users/currentUser/ohpc-ci-shadow/runs/de15e2c3afa3-20260816T093310Z-redis-tcl-run-4598`.
