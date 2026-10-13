# rsbackup 10.0 native OHOS adaptation

## Source and dependency evidence

- Upstream tag: `https://github.com/ewxrjk/rsbackup/tree/10.0`.
- Tag archive SHA-256: `5e7472435912241ef4cbbb621c14b3a519bb7bed9fd03f2e881703bc89902600`.
- On HarmonyOS PC 6.0/aarch64, `conan download` and `conan install`
  resolved published Boost 1.90.0.4.4, SQLite 3.53.4, rsync 3.3.0, and
  Automake 1.19 binaries. Boost 1.90.0.4.4 includes both UUID headers and
  `libboost_filesystem.so`. The plain Boost 1.90.0 package did not include
  the filesystem library; Boost 1.91.0.1.3 lacked the UUID header.
- Published rsync 3.3.0 reports `no ACLs`. Its `--xattrs` mode fails to read
  HMDFS `security.hmmac` with `EINVAL`.

## Portability changes

1. Make `rsbackup-graph` conditional on Cairomm and Pangomm, and keep its
   graph-only sources outside the core library.
2. Accept externally supplied SQLite flags when pkg-config's Autoconf macro
   is unavailable; link the published Boost filesystem library without the
   absent `libboost_system`.
3. Add configure switches for default rsync ACL and xattr preservation. The
   OHOS recipe disables both based on the published rsync and HMDFS behavior.
4. Include `<fcntl.h>` explicitly for `FileLock.cc`.
5. In `src/test-action.cc`, test the subprocess timeout by launching `sleep`
   directly. The OHOS shell wrapper returned status 0 after termination,
   hiding the signal status the test intends to verify.
6. Generate Autotools `config.status` temporary files under a writable build
   directory. Set `PWD` explicitly because nested HMDFS directories can
   intermittently fail `getcwd` in child shells.

## Tests

- Native `make -j1`: passed.
- Upstream `src` suite: 29/29 passed after the direct-subprocess test fix.
- Upstream `tests` shell suite: 25 passed, 4 skipped, 0 failed after
  platform-specific test repairs. The old fixture relied on unordered SQLite
  rows and unordered device diagnostics; the patch makes these deterministic.
  It also uses an absolute test root to avoid HMDFS `getcwd` failures and
  uses `/usr/bin/env bash` in two scripts. Three tests have explicit
  HarmonyOS-only exit-77 waivers: `issue37` (ACL preservation unavailable),
  `issue70` (HMDFS hard-link inode identity not stable), and `prune-timeout`
  (timeout hook status differs). Upstream `bashisms` already exits 77.
- Native end-to-end consumer check: passed. rsbackup invoked published rsync
  to back up a payload file, and the test compared the copied contents.
- Conan `conan create`: passed with published dependency binaries and full
  `make check`: 67 upstream tests (62 passed, 5 skipped, 0 failed) across
  C++, integration scripts, and tools scripts. The consumer end-to-end backup
  check passed. Final log SHA-256:
  `d2c98a0e8d73824ce1b70e2fbeb0c6f3da35a1e616c053919b1e052a17175588`.

The four upstream configuration-output fixtures are adjusted within the
recipe's build directory to reflect the two disabled rsync metadata options;
the source fixtures and other fields remain intact.

## 编译结束

Final native validation and its explicit test exemptions are recorded in
`reports/test-report.md`.
