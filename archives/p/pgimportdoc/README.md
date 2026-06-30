# pgimportdoc

command line utility for importing XML, JSON, BYTEA document to PostgreSQL

## Description

pgimportdoc is a PostgreSQL command line utility for importing XML, any text or
binary documents to PostgreSQL. It is the companion tool to pgexportdoc.

## Usage

```
pgimportdoc -c 'insert into xmltab(x) values($1)' -t XML -f myxmldoc
```

For help:
```
pgimportdoc --help
```

## Features

- XML documents are read in binary format with encoding handling
- Text documents are read in text format with client/server encoding translation
- BYTEA format supports bytea escaped text format
- Documents are completely loaded to client memory (max ~100MB practical limit)

## Build System

PGXS (PostgreSQL Extension Build System) - requires pg_config

## Dependencies

- PostgreSQL (libpq, libpgcommon, libpgport)

## Author

Pavel Stehule (pavel.stehule@gmail.com)