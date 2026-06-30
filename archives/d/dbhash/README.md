# dbhash

## Overview

dbhash is a command-line utility that computes the SHA1 hash of the schema and content of an SQLite database. It ignores extraneous formatting details and hashes only the database content.

## Features

- Compute consistent hash regardless of database file representation changes
- Compare databases to confirm equivalence
- Verify remote database content without full transmission

## Usage

```bash
dbhash [options] FILE ...

Options:
   --debug N           Set debugging flags to N (experts only)
   --like PATTERN      Only hash tables whose name is LIKE the pattern
   --schema-only       Only hash the schema - omit table content
   --without-schema    Only hash table content - omit the schema
```

## Example

```bash
dbhash mydatabase.db
8d3da9ff87196312aaa33076627ccb7943ef79e3 mydatabase.db
```

## Building

dbhash is part of the SQLite source tree (located at `tool/dbhash.c`). To build:

1. Obtain SQLite source code
2. Compile SQLite amalgamation (sqlite3.c)
3. Compile dbhash.c and link with sqlite3

```bash
clang -c -fPIC -O2 -DSQLITE_ENABLE_FTS5 sqlite3.c -o sqlite3.o
ar rcs sqlite3.a sqlite3.o
clang -c -fPIC -O2 -I. dbhash.c -o dbhash.o
clang dbhash.o sqlite3.a -o dbhash -lpthread -ldl -lm
```

## Source

- Official: https://www.sqlite.org/dbhash.html
- Source tree: https://www.sqlite.org/download.html (sqlite-src-*.zip)

## License

Public domain (SQLite blessing)