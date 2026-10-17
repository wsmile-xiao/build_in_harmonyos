# W0 Preflight Report

## Result

Preliminary adaptation can proceed. No Conan dependency package is required
for `pex`; its dependencies are external command-line tools used at runtime
or by the upstream test suite.

## Dependency Matrix

| Area | Requirement | Current host | Target action |
| --- | --- | --- | --- |
| Runtime | POSIX shell | Missing on Windows PATH | Provide `/system/bin/sh` |
| Runtime | `curl` | Available as Windows binary | Verify OHOS `curl` |
| Runtime | `git` | Available as Git for Windows | Verify OHOS `git` |
| Extension commands | `pg_config`, `psql` | Not available | Verify PostgreSQL environment on target |
| Upstream tests | Perl, `prove`, `make` | Missing | Provide in shadow CI/test image |
| Audit test | Perl `YAML` | Not checked | Install or accept the upstream skip |
| Conan | Conan 2 | Missing | Run recipe in adaptation environment |

## Split Decision

No separate Conan dependency adaptation is needed. If the target test image
lacks Perl/TAP tooling, that is an environment/toolchain prerequisite and
should be handled separately from the `pex` package change.

## Issue

No explicit issue number was found in the project files or supplied context.
Issue linkage is intentionally left pending per the current task instruction.
