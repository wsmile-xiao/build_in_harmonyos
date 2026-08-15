# Zabbix 7.4.5 - HarmonyOS PC Adaptation Notes

## Build Configuration

- **Platform**: OpenHarmony / HarmonyOS PC arm64
- **Compiler**: clang/clang++ 15.0.4
- **Build system**: Autotools (bootstrap.sh + configure + make)
- **Components enabled**: agent (zabbix_agentd), zabbix_get, zabbix_sender
- **Components disabled**: server, proxy, agent2, web service, Java gateway

## Source

- Official GitHub source archive (tag `7.4.5`, commit `c525822dce0239df36b656968561bbf57352cb4d`):
  `https://github.com/zabbix/zabbix/archive/refs/tags/7.4.5.tar.gz`
- SHA256: `de9ed613745a40314a2e7c69e67275c4f97be9a3ad8eeb3e356582aca197221e`
- GitHub archive contains `tests/` but no pre-generated `configure`; bootstrapped via
  `bootstrap.sh tests` (automake as tool_requires).

## Dependencies

- openssl/3.5.6.1.1, pcre2/10.45, zlib/1.3.1
- cmocka/2.0.2, libyaml/0.2.5 (mock data YAML)
- automake/1.18 (tool_requires)
- iconv: OHOS libc (HAVE_ICONV)

## Patches Applied (16)

1. `0001-resolver-capability-detection.patch` — complete resolver API feature
   detection in `m4/resolv.m4` (OHOS lacks `res_ninit`/`res_nsend`/`_res`).
2. `0002-cmocka-2.x-cm_print_error-compat.patch` — drop local `cm_print_error`
   forward declaration (clashes with cmocka 2.x).
3. `0003-zbxcommon-cmocka-cflags.patch` — add `CMOCKA_CFLAGS`/`YAML_CFLAGS`.
4. `0004-mock-data-yaml-ldflags.patch` — add `CMOCKA_LDFLAGS`/`YAML_LDFLAGS`.
5. `0005-wrap-calloc-realloc-real.patch` — `__wrap_calloc`/`__wrap_realloc` call
   `__real_*` outside the test path.
6. `0006-zbxtypes-lp64-format.patch` — detect LP64 via `__LP64__`.
7. `0007-pthread-process-shared-mmap.patch` — enable `HAVE_PTHREAD_PROCESS_SHARED`
   for cross-compile, move `LIBPTHREAD_CHECK_CONFIG` out of server/proxy block,
   replace SysV shm with `MAP_SHARED|MAP_ANONYMOUS` in `zbx_locks_create/destroy`.
8. `0008-shm-mmap.patch` — mmap-based `zbx_shm_create`/`zbx_shm_destroy`.
9. `0009-stats-shm-mmap.patch` — collector/diskstat shared memory on mmap.
10. `0010-dshm-mmap.patch` — dshm on mmap.
11. `0011-procstat-shm-mmap.patch` — procstat on mmap.
12. `0012-dummy-module-cc.patch` — dummy test module `$(CC) $(CFLAGS)`.
13. `0013-iconv-charset-normalize.patch` — strip surrounding double quotes /
    trailing backslash from the charset name before `iconv_open`, and return an
    empty result for un-detectable (non-ASCII) charset names. musl's iconv
    rejects these with EINVAL while glibc tolerates them; the old behavior made
    `zbx_convert_to_utf8` return NULL and crashed callers (SIGSEGV).
14. `0014-shm-named-posix.patch` — add POSIX named shared-memory primitives
    (`zbx_shm_create_named`/`zbx_shm_attach_named`/`zbx_shm_destroy_named` via
    `shm_open`+`ftruncate`+`mmap`) and carry a cross-process `name` in
    `zbx_dshm_t`/`zbx_dshm_ref_t`.
15. `0015-stats-diskstat-named-shm.patch` — switch diskstat shared memory from a
    process-local mmap address to a named `shm_open` segment so collector and
    listener processes can reattach after extension.
16. `0016-dshm-named-shm.patch` — `zbx_dshm_realloc`/`zbx_dshm_validate_ref`
    (procstat) re-map by name instead of copying a process-local address.

## Platform Adaptations (recipe-level)

- `-fno-builtin-realloc` (clang folds `realloc(NULL,n)` into `malloc(n)`).
- Global `-I`/`-L` for openssl/cmocka/libyaml.
- In-source build.
- SysV IPC → POSIX shared memory. OHOS blocks SysV IPC (`shmget` EACCES,
  `semget` SIGSYS) but supports PTHREAD_PROCESS_SHARED, mmap and `shm_open`.

### Shared-memory model

- Fixed-size, fork-before segments (process-shared locks, collector base data)
  use `MAP_SHARED|MAP_ANONYMOUS` mmap; they are inherited by forked children at
  the same virtual address and need no cross-process re-mapping.
- Resizable, fork-late segments (diskstat, procstat dshm) use named
  `shm_open`+`ftruncate`+`mmap(MAP_SHARED)` segments. The cross-process
  identifier stored in the shared collector data is now the segment **name**
  (not a virtual address); other processes re-attach via
  `zbx_shm_attach_named()`/`zbx_dshm_validate_ref()` after a resize.

## zabbix_agentd daemon (real TCP)

`zabbix_agentd -f` starts and listens on 127.0.0.1. Verified over TCP:
`agent.ping` → `1`, `system.hostname` → `localhost`.

## Shared-memory lifecycle test (test_package)

`test_package/shm_lifecycle_test.c` exercises the POSIX shm path end-to-end:
create (`shm_open`+`ftruncate`+`mmap`), fork a child that re-opens the grown
segment **by name**, resize (`ftruncate`), cross-process update, and cleanup
(`munmap`+`shm_unlink`). It passes on OHOS.

## Upstream cmocka Test Results (agent scope)

- Suites compiled: 126
- Total cases run: 2800
- Passed: 2799
- Failed: 1
- Skipped (not built): 3142 (server/proxy-only `if SERVER`/`if PROXY` suites)
- Errors: 0
- Pass rate: 99.96%

The single remaining failure:
- `calculate_item_nextcheck` "Scheduling check every day at 2 a.m. when
  government decides drastically change the timezone" (`:Pacific/Apia`, Samoa
  2011-12-30 skipped entirely). This is an upstream Zabbix limitation, not an
  adaptation bug: `scheduler_find_dst_change()` only compares `tm_isdst` (0↔1),
  but Samoa's transition changes only `tm_gmtoff` (-10:00 → +14:00) while
  `tm_isdst` stays 1. It fails on glibc the same way.

The test runner (`test_runner.py`) replaces the Perl harness and keeps YAML
timestamps, sexagesimal scalars, leading-`+` scalars and null-like scalars
(`NULL`/`~`/empty) as strings, matching libyaml's behavior (libyaml does not
apply the null implicit tag).

## HarmonyOS CLI / Integration Tests (test_package)

- `--version` / `--help` for agentd/get/sender: PASS.
- Real agentd daemon + zabbix_get TCP round trip: PASS (`agent.ping`=1,
  `system.hostname`=localhost). Config/PID/log in a writable temp dir; agent is
  reliably terminated.
- `shm_lifecycle_test` (create/multi-process access/resize/update/cleanup): PASS.

## Known Limitations

- DNS monitoring item (`net.dns`) disabled (incomplete resolver API on OHOS).
- Agent2 (Go-based) not built.
- One upstream DST edge case fails (see above; not OHOS-specific).
