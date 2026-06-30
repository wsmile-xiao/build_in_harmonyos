# pgtcl

Tcl extension for PostgreSQL, providing a Tcl interface to libpq (PostgreSQL client library).

## Description

Pgtcl is a Tcl package that provides a Tcl interface to the PostgreSQL database system. 
It allows Tcl scripts to connect to PostgreSQL databases, execute SQL commands, and 
process query results. The package supports both synchronous and asynchronous operations,
prepared statements, and large object handling.

## Version

Latest compiled: 3.1.1

## Dependencies

- Tcl 8.6+
- PostgreSQL libpq
- sqlite3 (optional, for pgtcl-sqlite features)

## Build Notes

- TEA extension (Tcl Extension Architecture) using autotools
- Source tarball from GitHub flightaware/Pgtcl
- Requires autoconf to generate configure script (not included in source)
- HarmonyOS platform needs HarmonyOS* added to Linux pattern in TEA macros
