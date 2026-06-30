# DBIish — Database connectivity for Raku

## Overview
DBIish provides database connectivity for the Raku programming language (formerly Perl 6). It offers a unified interface similar to Perl's DBI, supporting multiple database drivers:

- **DBDish::mysql** — MySQL/MariaDB driver
- **DBDish::Pg** — PostgreSQL driver
- **DBDish::SQLite** — SQLite driver
- **DBDish::SQLCipher** — SQLCipher (encrypted SQLite) driver
- **DBDish::Oracle** — Oracle driver
- **DBDish::TestMock** — Mock driver for testing

## HarmonyOS Build Notes
- Version 0.6.8 is the latest release
- This is a **pure Raku module** — no C compilation required
- A custom Makefile was created for HarmonyOS installation
- Module files are installed to `$PREFIX/share/perl6/site/lib/` and `$PREFIX/share/perl6/site/dist/`

## Runtime Requirements
- **rakudo** (Raku compiler/runtime) — required for any Raku module
- **NativeHelpers::Blob** — Raku module dependency
- **NativeLibs** (>= 0.0.9) — Raku module dependency
- Database client libraries (optional, per driver):
  - libmysqlclient for MySQL driver
  - libpq for PostgreSQL driver
  - libsqlite3 for SQLite driver
  - libsqlcipher for SQLCipher driver

## Installation
After deploying rakudo on HarmonyOS:
```bash
zef install DBIish
```

Or manually:
```bash
make install PREFIX=/path/to/usr/local
```

## Source
- Repository: https://github.com/raku-community-modules/DBIish
- License: BSD-2-Clause