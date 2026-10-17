# percona-server 8.4.10_10 adaptation notes

## Scope

- Upstream tag: `Percona-Server-8.4.10-10`
- Conan version: `8.4.10_10`
- Build system: CMake
- Current status: `built` after remote HarmonyOS PC `conan create`
  completed successfully
- Package scope: client library and client tools only, configured with `WITHOUT_SERVER=ON`

The earlier W0 blocker was `ncurses/6.4`. After the merged `ncurses/6.6` PR,
fresh `CONAN_HOME` checks can download `ncurses/6.6` and `openssl/3.5.6.1.1`
recipes from `ohpcd`, so the main recipe can proceed to implementation.

## Source

```text
url: https://codeload.github.com/percona/percona-server/tar.gz/refs/tags/Percona-Server-8.4.10-10
sha256: caa8318c2dfb4930eb27f0dbed882e3a869f0412efc674589cb10ab35c8c9617
top-level: percona-server-Percona-Server-8.4.10-10/
```

## Dependencies

- `openssl/3.5.6.1.1`: used through `WITH_SSL=system` and explicit
  `OPENSSL_*` cache variables. The custom `WITH_SSL=<path>` branch is avoided
  because it is oriented around copying shared OpenSSL libraries.
- `ncurses/6.6`: used for bundled editline's `FindCurses` probe through
  explicit `CURSES_*` cache variables.
- zlib, lz4, zstd, icu, protobuf, curl, and boost use the versions bundled in
  the Percona source tree for this first-stage package.
- tirpc/RPC is skipped for the OHOS client-only package. The current package
  disables server/router/NDB and no active client target consumes `ext::rpc`.
- coredumper is disabled because the source tree has `extra/coredumper` but no
  CMake project under that directory for this release archive.
- KMIP keyring is disabled because `extra/libkmip` is not populated as a CMake
  project in the release archive and is not needed for the client/library
  subset.
- OHOS libc exposes the resolver path used by upstream's Alpine branch
  (`res_init`/`res_search`), but not `res_ninit`/`res_nsearch`/`res_nclose`;
  the patch keeps DNS SRV enabled by selecting that resolver path behind an
  explicit capability macro.
- HarmonyOS PC HMDFS rejects configure-time convenience symlinks such as
  `bin -> runtime_output_directory`, `lib -> library_output_directory`, and
  `lib/plugin -> plugin_output_directory`; the patch skips those symlinks on
  OHOS and leaves the real output directories in use.
- CMake uses `try_run()` for `setns`, `clock_gettime`, and `CLOCK_REALTIME`.
  In the OHOS cross profile, preset `HAVE_SETNS_EXITCODE=1`,
  `HAVE_CLOCK_GETTIME_EXITCODE=0`, and `HAVE_CLOCK_REALTIME_EXITCODE=0` to
  keep configure deterministic.
- The libcno HTTP/2 huffman header generator is built as a target under
  `runtime_output_directory`; the patch calls it with
  `$<TARGET_FILE:cno_huffman_generator>` so the build does not rely on PATH
  lookup of a bare executable name.
- OHOS clang reports `__SIZEOF_WCHAR_T__=4` and `__WCHAR_WIDTH__=32`, but does
  not define `__STDC_ISO_10646__`. Bundled libedit treats unknown platforms
  without that macro as unsupported, so the patch adds a capability macro to
  the existing platform allow-list in `chartype.h`.
- Bundled libedit's `terminal.c` also needs termcap function prototypes. With
  the Conan ncurses headers used here, OHOS reaches the existing manual
  prototype fallback that upstream only enabled for Solaris, so the patch
  enables that fallback through the same capability macro.
- Bundled curl detects `linux/tcp.h`, but the OHOS SDK header chain redefines
  `sockaddr_storage` after `sys/socket.h`. The patch disables curl's
  `HAVE_LINUX_TCP_H` check on OHOS so curl uses the already available
  `netinet/tcp.h` path instead.
- Upstream calls `MYSQL_CHECK_RPC()` for all Linux builds. On OHOS client-only
  builds this needlessly pulls bundled tirpc into the build graph, and tirpc's
  Autotools `config.status` is sensitive to HMDFS temporary-directory behavior.
  The patch skips the RPC check for `OHOS AND WITHOUT_SERVER` instead of
  modifying bundled generated `configure` files.
- Several upstream custom commands use bare build-tool names even though the
  tools are CMake targets emitted under the build output directory. The OHOS
  patch uses `$<TARGET_FILE:...>` for `cno_huffman_generator`, `comp_client_err`,
  `comp_err`, `comp_sql`, the sys_schema `comp_sql` invocation, and
  `uca9dump`.
- The static client package still compiles C++ implementation objects. Its
  Conan metadata therefore propagates `c++`, `c++abi`, and `unwind` so a plain
  C consumer can link `libperconaserverclient.a`.
- Shared library targets such as `libmysql` and `json_binlog` create `.so`
  symlink steps that are not required for the static client package and can
  fail on HMDFS. The OHOS patch skips those shared targets while retaining the
  static client library and `json_binlog_static`.
- The keyring vault unit-test helper compiles `vault_curl.cc` directly. Linking
  `ext::curl` only from the final test executables leaves that helper without
  bundled curl include directories; system Linux headers can hide the missing
  target dependency. The helper now links `ext::curl` itself so its compile
  usage requirements are explicit on OHOS and other non-system-curl builds.
- The libmysqlgcs unit tests include generated XCom RPC headers. Production
  CMake enables bundled SunRPC headers for `WIN32 OR OHOS`, while the unit-test
  directory originally enabled those include paths only for Windows. The test
  condition now matches production so `rpc/rpc.h` is available on OHOS.
- The concurrent `Bgc_ticket_manager_test.Several_tickets_test` shared random
  state and entered its 300-worker loop before all workers had started. On
  OHOS this could hang nondeterministically. Patch 0047 gives each worker its
  own engine and distribution, then synchronizes all 300 workers before the
  original 100-loop workload begins. The workload size and assertions are
  unchanged.
- The full-server CTest run exposed a separate OHOS capability boundary in
  NDB test initialization: `NdbHW_Init()` reads Linux procfs/CPU-affinity
  state that is not readable from the target user context. Patch 0048 skips
  this optional hardware-statistics initialization on OHOS while preserving
  all non-OHOS behavior; it does not fabricate CPU or memory statistics.

## Full-server CTest follow-up

The final full-server CTest run listed and executed 142 tests. All 142 passed
with zero failures in 707.21 seconds, including the large, InnoDB, and small
aggregate targets. Patches 0049-0054 address the earlier NDB capability,
HMDFS temporary-file, IPv6 localhost, and CSR-version boundaries; patch 0055
prevents the OHOS libc-incompatible InnoDB thread-priority warning from being
reported as an MTR error.

## CMake configuration

Key cache variables:

```text
CMAKE_SYSTEM_NAME=Linux
CMAKE_SYSTEM_PROCESSOR=aarch64
HAVE_SETNS_EXITCODE=1
HAVE_CLOCK_GETTIME_EXITCODE=0
HAVE_CLOCK_REALTIME_EXITCODE=0
WITHOUT_SERVER=ON
WITH_ROUTER=OFF
WITH_NDB=OFF
WITH_UNIT_TESTS=OFF
WITH_EDITLINE=bundled
WITH_SSL=system
WITH_ZLIB=bundled
WITH_LZ4=bundled
WITH_ZSTD=bundled
WITH_COREDUMPER=OFF
WITH_COMPONENT_KEYRING_KMIP=OFF
WITHOUT_COMPONENT_KEYRING_KMIP=ON
WITH_AUTHENTICATION_CLIENT_PLUGINS=OFF
WITH_AUTHENTICATION_LDAP=OFF
WITH_AUTHENTICATION_KERBEROS=OFF
WITH_AUTHENTICATION_WEBAUTHN=OFF
WITH_PERCONA_AUTHENTICATION_LDAP=OFF
WITH_FIDO=none
WITH_KERBEROS=none
```

`CMAKE_SYSTEM_NAME=Linux` is intentional: upstream selects OS support by loading
`cmake/os/${CMAKE_SYSTEM_NAME}.cmake`, and the source tree has `Linux.cmake` but
no `HarmonyOS.cmake`.

## Upstream test inventory

The upstream source does contain tests. In the complete pinned
`Percona-Server-8.4.10-10` source snapshot, `mysql-test` contains 10,422
`.test` files and 10,261 `.result` files. The patched validation tree contains
26,985 files under `mysql-test` and 583 files under `unittest`. Its `README`
describes the `mysql-test-run.pl`/`mtr` framework, and `CONTRIBUTING.md`
requires at least the `main.1st` start-and-shutdown test for a full server
build. The earlier 148/1,457 inventory came from an incomplete sparse source
snapshot and is not used as upstream coverage evidence.

The current Conan package intentionally does not execute that suite. The
package sets `WITHOUT_SERVER=ON` and `WITH_UNIT_TESTS=OFF`; upstream CMake adds
the `mysql-test` directory only under `IF(NOT WITHOUT_SERVER)`, and adds the
unit-test directories only under `IF(WITH_UNIT_TESTS)`. A separate full-server
build is used for HarmonyOS PC MTR and unit-test validation. The package build,
full-server build, MTR run, CTest run, and consumer target execution are
reported as separate evidence stages.

## Verification

- W0 recipe publication gate: passed for `openssl/3.5.6.1.1` and `ncurses/6.6`
  in a fresh Conan home.
- Recipe files and test package have been added.
- Local static checks passed:
  - `python -m py_compile conanfile.py test_package/conanfile.py`
  - `git apply --check --unidiff-zero patches/0001-ohos-dns-srv-and-optional-kmip.patch`
    against a clean upstream source tree
- Remote HarmonyOS PC `conan source .` replayed the current patch
    successfully
  - All 46 pre-0047 patches were applied in order to the exact upstream tag, reversed
    back to a clean official tree, and applied a second time; both forward
    trees passed `git diff --check`.
- The final 0047 source was compiled into `merge_large_tests-t` on the target;
  the BGC test passed independently, and the complete 1,979-test GTest list
  passed in 16 exact-source shards with shard exit codes 0. BGC ran in its own
  process because the upstream singleton test can hang when preceded by other
  GTest suites on OHOS; the remaining shard-4 tests ran separately.
- The final 0048 source was compiled into `merge_innodb_tests-t` on the target.
  Its 952 parsed test entries ran in 16 exact-source shards; all 16 shard exit
  codes were 0. Each shard retained two upstream-disabled entries, so 920
  tests executed and passed. The raw archive is stored at
  `D:/codex/record/percona-server/8.4.10_10/device-tests/merge-innodb-r331.tar.gz`.
- Remote HarmonyOS PC `conan create` passed with exit code 0.
  Evidence:
  - validation log SHA256:
    `e026c23df450cb6528df956d55bb109b88a602f7acc170b791d955bca126919f`
  - package reference:
    `percona-server/8.4.10_10#0367aef34d81dbe7fc9bb0d58363ea2d:b32e95946afda220db8287f449b037f206c3d8ff#d8c734ff432db966e415c7cbc960b39b`
  - packaged library: `libperconaserverclient.a`
  - C consumer target: `[100%] Built target test_percona_server_client`
  - target execution output: `percona-client:8.4.10-10:80410:1`

This evidence covers build, package, C consumer link, and target execution for
the test package. It does not prove W4, PR CI, merge, or publication.

COMPLETED: remote HarmonyOS PC build/package/test_package validation passed; PR
submission gates remain tracked separately.
---

**编译结束**: 2026-08-12 16:47
**最终状态**: built
