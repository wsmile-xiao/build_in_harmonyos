# repmgr

repmgr is a suite of tools for PostgreSQL replication management, developed by EnterpriseDB.

## Description

repmgr provides tools to set up, monitor and maintain PostgreSQL replication clusters, including:
- `repmgr`: Command-line tool for managing replication
- `repmgrd`: Daemon for automatic failover monitoring
- PostgreSQL extension for replication metadata

## Version

Latest version: 5.5.0

## Build Requirements

- PostgreSQL 9.4+ (with libpq, pgcommon, pgport)
- curl
- json-c
- readline

## Build System

autotools (configure + make)

## Notes

- `make check` is not supported; testing requires a running PostgreSQL server via `make installcheck`
- On HarmonyOS, the `repmgr --version` command may fail to display due to getpwuid() limitations; `repmgrd --version` works correctly