# Redis 6.2 HarmonyOS adaptation notes

## Scope

- Requested package version: `redis/6.2`
- Upstream source mapped to the first stable 6.2 release: Redis 6.2.0
- Issue: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2145
- Build system: raw Makefile, native OHOS/aarch64 build

## Source and build analysis

The official tarball SHA256 was verified locally as
`67d624c25d962bd68aff8812a135df85bad07556b8825f3bcd5b522a9932dbca`.

Redis 6.2.0 builds bundled hiredis, linenoise, Lua, and hdr_histogram. The
recipe selects `MALLOC=libc`, disables optional systemd and TLS support, and
uses compiler paths from Conan's `tools.build:compiler_executables` conf.

Redis 6.2.0 calls `pthread_cancel`, `pthread_setcancelstate`, and
`pthread_setcanceltype`. The OHOS compatibility patch supplies these missing
symbols only when `__OHOS__` is defined. Unlike the Redis 8.6.0 archive, this
version has no `threads_mngr.c` atomic initialization issue, and its
`setproctitle.c` already guards glibc-only variables, so those patches were not
copied.

## Testing

`make test` is the upstream Tcl integration suite. It requires Tcl 8.5 or 8.6
and is intentionally retained in `build()`. The consumer test starts the
packaged server on loopback, verifies the server and client versions, exercises
PING, SET, GET, and DEL, and shuts the server down.

The OHOS adaptation also:

- runs upstream shell entry points explicitly through `sh`;
- avoids a `sizeof` expression in a preprocessor condition;
- disables Redis' unnecessary `-latomic` link flag because OHOS provides the
  required AArch64 atomics without a separate `libatomic`;
- signs the target executables before running the upstream suite;
- gives the Tcl suite a unique short Unix-socket-capable temporary root under
  `/data/storage/el2/base/cache`, then removes it in a `finally` block; and
- reads the numeric UID from `/proc/self/status` when the OHOS account is not
  present in the user database used by `id -u`.

## Dependency resolution

W0 identified `tcl/8.6.16` as the only build-time test dependency. Its package
initially omitted Tcl Modules, so Redis reached the upstream suite but failed
when `clock format` requested `msgcat 1.6`. That dependency fix was kept out of
this branch and completed separately under issue 2149; the validated Tcl
recipe revision is `2b0403fc1121633897928693fa91bfbe` and the package revision
is `55eecfe40ee5dc1d5c7a5b6a181c61cf`.

PR CI build `#25490` compiled Redis but failed when `make test` could not find
Tcl, even though the recipe declared `tcl/8.6.16` as a tool requirement. The
recipe now obtains Tcl's `package_folder` directly from Conan's build dependency
graph and generates `redis_tcl_env`. That environment explicitly provides
`PATH`, `TCL_ROOT`, `TCL_LIBRARY`, and `LD_LIBRARY_PATH` to both build commands.
Generation also verifies `tclsh8.6`, `init.tcl`, and the `msgcat 1.6` Tcl Module
before the lengthy Redis build starts.

## CI portability follow-up

The corrected Tcl dependency from issue 2149 is now merged and published.
Official CI build `#26396` passed dependency setup and entered the upstream
suite, where `tests/unit/oom-score-adj.tcl` failed before its assertions because
`id -u` could not map OHOS UID 20020099 through the user database. Patch 0006
retains the full test and falls back to the numeric `Uid:` field in
`/proc/self/status`; it reports an explicit error if neither source is usable.

## Shadow CI validation

The single-package OHOS shadow CI run passed on 2026-08-15 (Asia/Shanghai):

- Redis commit: `f14a117dfb92ab541aeff901bf2be24c288f3062`
- Run directory:
  `/storage/Users/currentUser/ohpc-ci-shadow/runs/f14a117dfb92-20260814T160242Z-redis-tcl-run-47996`
- Dependency cache SHA256:
  `3b742a313f08c8081898f419f97fa75cd8693c1d5e1c06056b9d95fb93972afe`
- Build log SHA256:
  `529fee6f2a24ca699962cfb18f307a76409f5084d5875d425b2080bfb8317d23`
- Package reference:
  `redis/6.2#724a194533b504f5a94a1dab07649b30:6b129b068851896169fae42d399fa922d239ce8a#b7e64077f4a1871b96e9fec2926ddf57`
- Upstream suite: all 63 parallel test units plus the solo defrag test passed
  without errors, covering 1,824 successful assertions.
- Consumer test: version checks and the loopback service flow passed.
- Gates: L0, L1, L2, L4, and L5 passed; the destructive L1e check also
  confirmed that the consumer test depends on the packaged Redis binaries.
- Cleanup: no Redis/Tcl test processes and no `redis-test-*` cache directory
  remained after the run.

`redis-check-aof` and `redis-check-rdb` produced non-blocking L2 warnings because
these data-file checkers do not implement the same version/help interface as
the other packaged commands. Their packaging was still covered by L5, while
the executable service paths were covered by the upstream and consumer tests.

### Tcl environment follow-up

The explicit Tcl environment fix was revalidated on the OHOS device against
the same dependency recipe and package revisions listed above:

- Base Redis commit: `685b27698bde23307ee71caefde8b5efea3ea2d9`
- Isolated directory:
  `/storage/Users/currentUser/ohpc-ci-shadow/current-head-tests/redis-685b2769-tcl-env`
- Updated recipe SHA256:
  `c5502150bda4eec09c5e944325a23c24d821b93de24af49d77d6c8ba928ee580`
- Final environment-generation log SHA256:
  `71258107ef13ccfda6b86b7659e97c3825c5852227cb09d7ac753d6569f131a7`
- Full `conan create` log SHA256:
  `b3f5e9c186ed75d37f767d786a0f0f04ea7f26b9be1641dbcee9516ae65c0e83`
- Package reference:
  `redis/6.2#5ae9a424625d4298e497999642ced41a:6b129b068851896169fae42d399fa922d239ce8a#1ce65bc7598568336d0a0a31e335c3a4`
- Environment probe: packaged `tclsh8.6` resolved from `PATH`, `msgcat`
  returned `1.6.1`, and `clock format` returned `1970-01-01`.
- Upstream suite: all 63 parallel units plus `defrag` passed without errors.
- Consumer test: the packaged Redis 6.2.0 loopback service flow passed (6/6).

## Reproduction commands

On an OHOS worker with the fixed Tcl package available, run only Redis:

```sh
CI_PACKAGES="archives/r/redis/6.2" zsh ci/conan/build_and_test.sh
```

Direct Conan diagnostic command (using the worker's configured OHOS profiles):

```sh
conan create archives/r/redis/6.2 --user=ohpcd --channel=stable \
  -pr:h="$HOME/.conan2/profiles/ohos" \
  -pr:b="$HOME/.conan2/profiles/ohos" --build=missing
```
