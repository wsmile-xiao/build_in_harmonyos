# pgcopydb

`pgcopydb` is a command line tool that automates copying a PostgreSQL database
from a source instance to a target instance: it drives `pg_dump`/`pg_restore`
for the schema and its own libpq workers for the data, then optionally follows
the change stream (logical decoding) to keep the target up to date.

- Upstream: <https://github.com/dimitri/pgcopydb>
- License: PostgreSQL License

## Versions

- 0.18: Conan-adapted for HarmonyOS PC (aarch64), built with the upstream
  Makefile against `postgresql/18.3` and `gc/8.2.12`.

## HarmonyOS notes

The platform sandbox rejects the System V IPC system calls with `SIGSYS`
(`semget`, `semctl`, `semop`, `msgget`, `msgsnd`, `msgrcv`, `msgctl`), which
kills the process with `Bad system call` before it prints anything, and musl's
`getopt_long()` ignores `POSIXLY_CORRECT`, which breaks the sub-command
dispatching.  Both are handled by a single portability patch that keeps the
portable System V code in place and selects POSIX based implementations through
semantic capability macros defined by the recipe for OHOS builds only; see
`0.18/notes.md` for the details.
