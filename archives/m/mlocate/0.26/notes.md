# mlocate 0.26

**Build system:** Autotools  
**Source:** https://releases.pagure.org/mlocate/mlocate-0.26.tar.xz  
**SHA256:** `3063df79fe198fb9618e180c54baf3105b33d88fe602ff2d8570aaf944f1263e`

## Adaptation notes

- E011: HMDFS rejects writes inside private Autotools temporary directories. The portability patch changes their umask to 022.
- E046: HMDFS cannot be relied on to retain setgid executable bits. `Autotools.install()` runs the upstream privileged install hook, but the package does not rely on its ownership or setgid changes and supports a user-owned database.
- The upstream `locate` startup guard required read and search access to `/`; HarmonyOS exposes `/` as search-only (0711). The patch checks search permission only, so database queries can run (related to E303).

## Discoveries and findings

- ✅ Old Autotools configure code may set umask 077 for generated files; use 022 for writable HMDFS build directories (E011).
- ✅ mlocate's `access("/", R_OK | X_OK)` startup guard rejects HarmonyOS's search-only root; checking `X_OK` allows traversal while each database file remains checked normally (E303).
- ✅ HMDFS cannot represent case-distinct path names or enforce the upstream chmod test matrix, so those upstream groups require explicit platform exclusions (E193, E046).
- ✅ The upstream install hook attempts chgrp and setgid changes, but a user-owned database works without relying on either privileged behavior (E046).

## Package contents

- `locate` and `updatedb` are installed in the Conan package `bin/` directory.
- The upstream build also installs manual pages and the database directory skeleton.
- `Autotools.install()` invokes the upstream `install-exec-hook`, which attempts `chgrp` and conditionally sets locate setgid. The package does not depend on those changes; users create and query a database they own with `updatedb -U` and `-o`.

## Tests

- Upstream Autotest: 34 supported scenarios passed; 3 upstream skips remain, and 8 platform-incompatible groups are excluded. The suite uses `TESTSUITEFLAGS` to omit case-sensitive filename tests, hardlink/FIFO and deep-directory tests, and chmod enforcement tests on HMDFS. The recipe invokes the upstream `make check` target.
- Consumer `test_package/test.sh`: version checks, creates a database from a temporary fixture, and verifies the installed `locate` returns the indexed path (4 checks).
- Clean G0 configure/build passed. Conan create and the consumer test passed; `test_package/test.sh` verified versions, database creation, and query results 4/4.
---

**编译结束**: 2026-09-29 00:36
**最终状态**: built
