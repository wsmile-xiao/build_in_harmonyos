# netsurf-buildsystem 1.1 validation report

## Test inventory

| Scope | Result | Command and evidence |
| --- | --- | --- |
| Upstream registered test cases | 0/0 NOT_APPLICABLE | `make -C source/buildsystem-1.1 test` returned RC 0; the upstream target is intentionally empty and therefore contributes no test-case denominator |
| Conan package creation | 1/1 PASS | `conan create archives/n/netsurf-buildsystem/1.1 --build=missing` returned RC 0 |
| Installed consumer compile/archive | 1/1 PASS | `test_package/test.sh` used installed `Makefile.tools` and `Makefile.top` to compile `smoke.c` and produce `libsmoke.a` |
| Platform W3 r4 transaction | PASS | `w3-r4-release-postrelease.log` |
| Local CI setup/build scripts | 2/2 PASS | `ci-metadata.json` |

## Platform transaction

- Endpoint: `10.62.195.15:8022`
- Run: `netsurf-buildsystem-1.1-w3-r4-20260903`
- Terminal: `POSTRELEASE_PASS`, `root_removed=true`
- Receipt log SHA-256: `9AB0BACDF0B392CE2054BE68CE5F9AF0D91BABB94F568073A8E0CD12EC4E92A0`

## Limitations

This package contains build metadata and helper scripts, so no executable or
library is expected in `bin/` or `lib/`. The official upstream `make test`
command succeeds but its target is intentionally a no-op, so it is recorded as
0/0 NOT_APPLICABLE rather than as one upstream test case. The installed
consumer fixture performs the real 1/1 compile-and-archive check through
`Makefile.tools` and `Makefile.top`.

Conan create log SHA-256: `5D24DDAB43477EE967A2F3E032B6B0428CCA4E3EAB495EA3A9A0E27381159A8D`
