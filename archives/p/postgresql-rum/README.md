# postgresql-rum

## Description

RUM index access method for PostgreSQL. This module provides access method to work with RUM indexes, which is based on the GIN access method code.

RUM solves performance issues with GIN indexes by storing additional information in a posting tree, providing:
- Faster ranking (stores positional information)
- Faster phrase search
- Faster ordering by timestamp
- Possibility to perform depth-first search

## Compilation Status

**Version**: 1.3.15
**Status**: Published
**Date**: 2026-06-03

### Dependencies

- PostgreSQL 17.0

### Build System

- PGXS (PostgreSQL Extension Building Infrastructure)

### Installation

```bash
# Install precompiled package
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- postgresql-rum 1.3.15

# Or compile from source
make USE_PGXS=1 PG_CONFIG=$(which pg_config)
make USE_PGXS=1 install
```

### Usage

After installation, create the extension in PostgreSQL:

```sql
CREATE EXTENSION rum;
```

## License

PostgreSQL License (similar to PostgreSQL license)

## Homepage

https://github.com/postgrespro/rum