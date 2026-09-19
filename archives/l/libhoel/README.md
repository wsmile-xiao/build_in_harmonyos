# libhoel

C Database abstraction library with json based language (part of the
babelouest/ulfius stack).

- Upstream: https://github.com/babelouest/hoel
- License: LGPL-2.1-or-later
- Language: C99

## Supported database backends

- sqlite3 — enabled (sqlite3/3.53.4 from the ohpcd registry)
- MariaDB — **disabled on OHOS** (client library not available on the
  ohpcd conan registry; `WITH_MARIADB=OFF`)
- PostgreSQL — **disabled on OHOS** (client library not available on the
  ohpcd conan registry; `WITH_PGSQL=OFF`)

## Versions

| Version | Status |
|---------|--------|
| 1.4.29  | built (HarmonyOS PC, aarch64, static) |

## Dependencies

- Runtime: orcania, libyder, jansson, sqlite3
- Test-build only: check (upstream CTest suite: core + multi)
