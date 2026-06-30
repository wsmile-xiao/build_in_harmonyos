# postgresql-uint

PostgreSQL unsigned integer type extension.

## Description

This extension provides unsigned integer data types for PostgreSQL:
- **uint1**: 1-byte unsigned integer (0 to 255)
- **uint2**: 2-byte unsigned integer (0 to 65535)
- **uint4**: 4-byte unsigned integer (0 to 4294967295)

## Source

- **Repository**: https://github.com/nad2000/postgresql-contrib-uint
- **Latest Version**: 3.0.0
- **Supported PostgreSQL**: 13.x, 14.x, 15.x, 17.0

## Build System

- **Type**: PGXS (PostgreSQL Extension Building Infrastructure)
- **Requirements**:
  - PostgreSQL development files (pg_config)
  - C compiler (clang)

## Usage

After installing the extension:

```sql
-- Create extension
CREATE EXTENSION uint;

-- Create table with unsigned integers
CREATE TABLE utable (id uint4, val8bit uint1);

-- Insert data
INSERT INTO utable VALUES (1, 2), (3, 4), (5, 6);

-- Query data
SELECT * FROM utable;
```

## Installation

The precompiled package installs the extension files to:
- `$PREFIX/lib/postgresql/uint.so` - Shared library
- `$PREFIX/share/postgresql/extension/` - Extension definition files

## Compiled Versions

- **3.0.0**: Built successfully on 2026-06-03
