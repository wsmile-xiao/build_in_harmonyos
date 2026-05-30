# mdbtools

MDB Tools is a set of tools and libraries for reading Microsoft Access database (MDB) files.

## Available Version
- 1.0.1 (2026-05-19): Static libraries for OpenHarmony

## Description
mdbtools provides:
- libmdb: Library for reading MDB file format
- libmdbsql: SQL query support for MDB files

## Dependencies
- glib
- bison
- flex

## Usage
Static libraries can be linked in your applications to read Access database files.

## Build Status
- 1.0.1: published (static libraries available)

## Notes
Command-line tools (mdb-export, mdb-tables, etc.) are not included due to linking issues.
