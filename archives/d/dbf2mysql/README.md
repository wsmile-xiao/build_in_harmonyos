# dbf2mysql

dbf2mysql is a pair of command-line converters between xBase DBF files and
MySQL-compatible databases. The package installs `dbf2mysql` and `mysql2dbf`.

- Homepage: https://dbf2mysql.sourceforge.net/
- License: Public Domain (upstream README grant)
- Category: database utility

## OHOS notes

The legacy MySQL C API is provided by `mariadb-connector-c`. A small source
patch replaces the removed `mysql_connect()` API with `mysql_real_connect()`.
