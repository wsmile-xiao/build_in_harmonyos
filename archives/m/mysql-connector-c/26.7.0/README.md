# mysql-connector-c 26.7.0

> The Conan package name `mysql-connector-c` here maps to **MySQL Connector/C++
> 26.7.0** (Oracle's official source distribution).  The C API is exposed via
> `<mysqlx/xapi.h>` — the "X DevAPI for C" subset of the connector.

## What it is

MySQL Connector/C++ 26.7.0 provides a JDBC-like C++ API and a plain-C API
("X DevAPI for C") for talking to MySQL 8.0+ servers via the X Protocol.

This recipe builds only the X DevAPI for C portion (no JDBC, no C++ API surface
in the public Conan target name).

## OHOS adaptation notes

- First-pass target: **static library** (`libmysqlcppconnx-static.a`).
- All non-OpenSSL dependencies (lz4, zstd, zlib, protobuf-3.19.6, RapidJSON)
  are **bundled in `cdk/extra/`** and built in-tree.  No extra Conan
  dependencies required.
- `WITH_JDBC=OFF`: JDBC requires the libmysqlclient backend, which is out of
  scope for the C API.
- `WITH_TESTS=OFF`: disable upstream ctest.
- `OPENSSL_*` cache variables: see `conanfile.py` and `notes.md`.

## Conan references

- `name`: `mysql-connector-c`
- `version`: `26.7.0`
- upstream header (C API): `mysqlx/xapi.h`
- upstream library: `mysqlcppconnx`

## References

- Official download: <https://dev.mysql.com/downloads/connector/cpp/>
- Source repository: <https://github.com/mysql/mysql-connector-cpp>
- X DevAPI for C docs: <https://dev.mysql.com/doc/dev/connector-cpp/8.0/>
