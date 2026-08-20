# ephemeralpg

ephemeralpg provides `pg_tmp`, a tool that spins up an isolated, temporary
PostgreSQL database for running tests. It reduces the wait time for a new
database to under one second by initializing a database in the background that
is reused by subsequent invocations.

The `3.4` recipe builds the upstream Makefile and produces two executables:

- **getsocket** — a small C program that fetches an unused TCP port (compiled
  from `getsocket.c`).
- **pg_tmp** — a POSIX shell script (generated from `pg_tmp.sh` via sed version
  substitution) that manages a temporary PostgreSQL cluster.

The recipe has no Conan package requirements; PostgreSQL is a runtime-only
dependency (`pg_tmp` shells out to `initdb`/`pg_ctl` at runtime). It uses the
OpenHarmony system C/POSIX interfaces and packages the two executables and
their manual pages.
