# scamper 20260713 adaptation notes

## Configuration

- Build the static measurement utility and helper libraries with select-based I/O.
- Disable privilege separation, io_uring, and debug files; enable the upstream
  test suite.
- Keep the portable trace, ping, DNS, HTTP, and UDP measurement modules enabled.

## Verification

- The consumer test executes `scamper -v` without raw-socket operations.
- The recipe runs all 37 programs dispatched by `tests/unit-all.pl` whenever
  the target profile is runnable.
- A source-wide scan confirms `HAVE_IPTABLES` and `ip_tables.h` occur only in
  `internal.h`; no iptables types, constants, or functions are referenced.
- The configure temporary-directory umask remains `077` on Linux and changes to
  `022` only for an OHOS host, where HMDFS rejects the upstream mode.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
