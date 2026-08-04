# virtualpg 2.0.1 W0 dependency report

## Routing result

`virtualpg/2.0.1` is a real build-time prerequisite of `spatialite-gui/2.1.0-beta1`, which consumes VirtualPG headers and pkg-config metadata. The main adaptation therefore remains paused until this dependency is merged and published. The dependency work is tracked by the existing unique Issue #1641 and its existing contrib claim; this run did not create or claim either item again.

VirtualPG itself can proceed because every direct third-party Conan requirement is already published for OHOS/armv8.

## Upstream dependency evidence

The exact official VirtualPG 2.0.1 source declares both dependencies in `configure.ac`:

- lines 22-23 require `sqlite3ext.h` and `sqlite3.h`;
- lines 54-71 require a usable `pg_config` query tool;
- lines 81-89 require `libpq-fe.h` and link-test `PQconnectdb` from `libpq`;
- line 94 link-tests `sqlite3_prepare_v2` from `libsqlite3` with `-lm`.

The Conan recipe maps those requirements to exact references `sqlite3/3.49.1` and `libpq/18.1`. It has no other third-party Conan requirements.

## Published binary evidence

An isolated HarmonyOS 6.0/AArch64 run resolved both dependencies from `ohpcd` with `--build=never`; neither was built from source:

| Dependency | Recipe revision | Package ID | Binary revision |
| --- | --- | --- | --- |
| `sqlite3/3.49.1` | `669361066cc2c76e0ed897e6b6a27e38` | `6b129b068851896169fae42d399fa922d239ce8a` | `9bae7e00509d3fd4c2f65da552f63fad` |
| `libpq/18.1` | `6f9e9c128f7c346abe8bbf26fa729453` | `01d92cf349a0dd98ff915f4bd99a04430171517f` | `f5e4e7897968df850e6f578157f31290` |

The shared and static target builds both completed with those exact dependency binaries. W0 therefore has no deeper missing dependency, and adaptation may continue at this leaf of the dependency chain.
