# DRAFT-mysqltuner-test-boundary-mysqladmin - upstream CLI tests can hide real mysqladmin dependencies

- Trigger event: mysqltuner 2.9.1 upstream TAP selection
- Path: Path B knowledge extension
- Phase: build() test triage

## Symptom

`tests/cli_validation.t` looked like a no-service CLI validation file. On the
OHOS device it passed 8 assertions and failed the authentication case:

```text
Couldn't find an executable mysqladmin/mariadb-admin command.
doesn't match 'Attempted to use login credentials, but they were invalid'
```

## Root Cause

The test invokes:

```perl
perl mysqltuner.pl --user nonexistent --pass wrong
```

That path needs `mysqladmin` or `mariadb-admin` before it can reach the expected
invalid-credentials diagnostic. On a build worker without a database client,
the script fails earlier with a tool-discovery error. The test is therefore not
a no-service build-time test even though most of the file only checks option
parsing.

## Fix

Keep `mysqladmin` and database-client validation out of the package PR unless
those dependencies are adapted and published separately. For mysqltuner, the
build-time upstream TAP subset was narrowed to files that do not need external
database client commands:

```text
tests/cli_options.t
tests/cli_forcemem_human.t
tests/version_consistency.t
tests/unit_version_helpers.t
tests/unit_cli_helpers.t
tests/unit_utilities.t
```

`tests/cli_validation.t`, real audit tests, MCP E2E tests, and database lab
tests are deferred to a database-client environment.

## Verification

The reduced subset ran on OHOS shadow CI with 6 files and 65 TAP assertions,
all passing. The package-level `test_package` still verifies real package
layout, launchers, data files, `--help`, memory options, and invalid port
handling through the packaged Perl runtime.

## Reuse

For CLI tools that wrap external service clients, classify tests by command
discovery as well as by file name. A test named "cli" may still require
database, network, or daemon clients.
