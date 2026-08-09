# libspatialite 5.1.0.1 adaptation notes

## Scope

- Package version `5.1.0.1` is the first Conan/OpenHarmony recipe revision of upstream `5.1.0`.
- GEOS, RTTOPO, PROJ, libxml2, GeoPackage, iconv and full EPSG data are enabled for the spatialite-gui dependency contract.
- FreeXL and MiniZIP are optional upstream features and remain disabled.

## Dependencies

- `sqlite3/3.49.1`
- `zlib/1.3.1.1`
- `proj/9.3.1.1`
- `geos/3.13.1`
- `librttopo/1.1.0.1`
- `libxml2/2.15.3`
- iconv is provided by the OpenHarmony musl libc.

W0 resolved the original five-package graph with `--build=never`. The archived
`libxml2/2.13.5` reference is not published, so this recipe uses the newer
published `libxml2/2.15.3` package. The RTTOPO prerequisite is pinned to the
merged correctness revision `librttopo/1.1.0.1`; its release upload remains a
separate formal gate.

Target execution established that disabling RTTOPO leaves 28 of the 108
registered upstream tests failing after the other five dependencies pass.
Upstream `configure.ac` requires `librttopo >= 1.1.0` to define
`ENABLE_RTTOPO`, so `librttopo/1.1.0.1` is a real prerequisite rather than an
optional test-only package. Final W0 remains open until that exact Conan
reference is published.

A fresh Conan home on the HarmonyOS target calibrated that result against the
published `geos/3.13.1` control after the librttopo PR was merged. The control
graph and binary completed with empty `info_invalid`; its validation record has
SHA-256 `6d556c0aee7b4c01a20974490a5cba3c30597b23c3c4a357c49b5dd357e17fdc`.
The exact `librttopo/1.1.0.1` install then returned
`Unable to find 'librttopo/1.1.0.1' in remotes`; that log has SHA-256
`28a86f8af5cbcb632a6b55e370bafab12cf6d9dbe8e2d0c1f5880893b9057926`.
The separate `conan download` acceleration-policy error is retained as
inconclusive and is not used as the publication decision. Local pre-publication
validation exports the exact merged librttopo recipe into an isolated cache;
it cannot satisfy or replace formal W0.

## Build Decisions

- The official source archive and SHA-256 are recorded in `conandata.yml`.
- Fresh-source patches add the `aarch64-unknown-linux-ohos` canonical triplet and move the generated `config.status` temporary directory under `TMPDIR` with an HMDFS-safe umask.
- libxml2 2.15 removed its built-in nano HTTP client. `reset_wfs_http_connection()` now calls `xmlNanoHTTPCleanup()` only when `LIBXML_HTTP_ENABLED` identifies the legacy client; with 2.15 there is no HTTP proxy state to reset.
- Upstream requires an executable `geos-config`. The recipe builds and signs a tiny adapter from the exact Conan GEOS include/lib directories instead of executing a package-cache shell script from HMDFS.
- Shared builds use Libtool `-avoid-version` for both `libspatialite.so` and `mod_spatialite.so`, preventing copied version aliases and preserving one stable SONAME on HMDFS.
- The signed test ELFs remain behind Libtool shell wrappers. Automake uses `LOG_COMPILER=/system/bin/sh` so the system shell parses those wrappers without relying on forbidden direct HMDFS script execution.
- The Conan consumer compile, signing and execution steps run with `TMPDIR`
  and `TMPPREFIX` under their writable build folder because the HarmonyOS
  system temporary mount is read-only. Its explicit link closure includes
  `librttopo` together with the other enabled dependencies.
- The consumer includes `sqlite3.h` before `spatialite.h`, matching upstream
  tests and the public-header contract: SpatiaLite declarations expose
  `sqlite3` and `sqlite3_int64` without including SQLite's declarations.
- Because the consumer directly calls SQLite APIs, its recipe declares the
  exact `sqlite3/3.49.1` requirement. Conan dependency nodes whose binaries
  were legitimately pruned do not contribute placeholder relative include or
  library directories to the manual compiler command.
- All build and test commands are serial (`-j1`).

## Upstream Test Compatibility

- `check_spatialindex.c` used `strcmp(result, "0") != 1` for two successful
  operations. The C contract guarantees only a negative, zero or positive
  result; the OHOS libc returned `128` for `strcmp("1", "0")`. Both checks now
  compare the exact expected value (`"1"`) for equality, without changing the
  operation or accepting a broader result set.
- GEOS 3.13.0 introduced a documented breaking change that treats zero-length
  LineStrings as points in boolean predicates. The pinned GEOS 3.13.1 C API on
  HarmonyOS returned `0,0,1,0,0,1,0,0` for the eight predicates in both
  `relations7.testcase` and the reversed-operand `relations8.testcase`, rather
  than their pre-3.13 expectations. The SQL statements and cases remain intact;
  only the eight expected values in each case are updated. Both testcases are
  exercised by all four SQL runners (`check_sql_stmt`, `check_sql_stmt_tiny`,
  `check_sql_stmt_legacy` and `check_sql_stmt_extension`).
- The behavior was reproduced independently with the published
  `geos/3.13.1` package on a second HarmonyOS PC using
  `GEOS 3.13.1-CAPI-1.19.2`. The upstream basis is the GEOS 3.13.0
  `NEWS.md` breaking-change entry; this is not an OHOS-only expectation.

## Validation Contract

- Upstream `test/Makefile.am` registers 79 base tests and 29 GeoPackage tests, for 108 independent Automake `TESTS` entries.
- The recipe first builds the complete test inventory, signs target ELFs, and then runs the unchanged `make -j1 check` suite through `/system/bin/sh`.
- `test_package/test.c` separately exercises 16 public SQLite/SpatiaLite lifecycle and feature assertions, including a GEOS buffer and a PROJ transformation, plus one cleanup regression that forces `sqlite3_close()` to return `SQLITE_BUSY` and verifies the shutdown path still runs exactly once.
- Formal test results and hashes are written only after target execution completes.

## Knowledge References

- `autotools-mkdir-p-hmdfs`
- `openharmony-pc-libtool-avoid-version-hmdfs`
- `E005` (static library linked into a shared object must be PIC)
- `E264` draft (derive a signed native `*-config` adapter from the exact Conan dependency metadata)
