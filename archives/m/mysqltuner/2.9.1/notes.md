# mysqltuner 2.9.1 HarmonyOS adaptation notes

## Scope

- Package: `mysqltuner/2.9.1`
- Upstream: `major/MySQLTuner-perl` tag `v2.9.1`
- Source archive SHA256: `384e4128991fb8573a61841cb838a74d59063607a817b1da6c86739e439eb4c2`
- Issue: ignored per current task instruction.

## W0 Dependency Check

- Required Conan dependency: `perl/5.42.2`
- External runtime commands for real audits: `mysql` or `mariadb`, plus `mysqladmin` or `mariadb-admin`
- Optional Perl module: `JSON` for JSON/trend comparison output paths
- Optional upstream E2E test tools: Docker, Python3, and a live MariaDB/MySQL container
- Missing dependency split required: no for the pre-adaptation package; database client availability remains a runtime environment prerequisite, not a bundled dependency in this PR.

## Source And Build Analysis

`mysqltuner` is a pure Perl application.  The upstream archive contains one main script (`mysqltuner.pl`), runtime data (`basic_passwords.txt`, `vulnerabilities.csv`), docs, a Makefile, helper scripts, and `tests/`.

The upstream `make unit-tests` target calls `perl build/audit_tests.pl`, which in turn runs syntax checks and `prove` over `tests/`.  The archive has 111 `tests/*.t` files.  Not all of them are suitable for a no-service Conan build: `tests/e2e_mcp_server.t` requires Docker, Python3, and a live MariaDB container, and lab targets require external database environments.

The Conan recipe therefore runs `perl -c mysqltuner.pl` plus this selected no-service TAP subset when `can_run(self)` is true:

- `tests/cli_options.t`
- `tests/cli_forcemem_human.t`
- `tests/version_consistency.t`
- `tests/unit_version_helpers.t`
- `tests/unit_cli_helpers.t`
- `tests/unit_utilities.t`

These files report 65 TAP assertions on the OHOS shadow-CI device.  Full database lab, MCP E2E, and `tests/cli_validation.t` authentication checks that require `mysqladmin`/`mariadb-admin` are deferred to a database-client test environment.

## Packaging

- Installs `bin/mysqltuner` and `bin/mysqltuner.pl`
- Installs `share/mysqltuner/basic_passwords.txt`
- Installs `share/mysqltuner/vulnerabilities.csv`
- Installs `share/doc/mysqltuner/README.md` and `USAGE.md`
- Installs `licenses/LICENSE`
- On OHOS, rewrites the script shebang to `/data/service/hnp/bin/perl`
- Exposes Perl and package `bin/` paths through `runenv_info`

## Test Evidence

- Source archive download and SHA256 verification: passed locally.
- Archive structure check: passed locally; includes required script/data/license files and 111 upstream `.t` files.
- Python syntax check for new recipe and test helper: passed locally via `compile()` text checks.
- YAML/key field check: passed locally.
- `git diff --check`: passed locally.
- Conan create: not run locally because current Windows PATH has no `conan`.
- Perl upstream/test_package execution: not run locally because current Windows PATH has no `perl`.
- True-device/shadow CI: passed on OHOS aarch64 with `CI_PACKAGES="archives/m/mysqltuner/2.9.1"`.
- Shadow CI L0: passed. `perl/5.42.2` is available in `ohpcd`; `mysqltuner/2.9.1` is not yet published.
- Shadow CI build(): `perl -c mysqltuner.pl` passed; `perl -S prove` ran 6 upstream TAP files, 65 tests, result PASS.
- Shadow CI test_package: executed successfully through Conan VirtualRunEnv, then L1e destructive negative test passed.
- Shadow CI L5: passed; package has `bin/` content.
- Shadow CI L2: non-blocking skip for direct `mysqltuner --help` on the hmdfs Conan cache.  The packaged script is mode `0750`; explicit Perl execution under Conan runenv was verified separately with `--help` exit 0.

Two CI-environment adjustments were needed for the manual isolated run:

- Run `ci/conan/setup.sh` first inside the isolated `CONAN_HOME` so `ohpcd` is configured and `conancenter` is disabled.
- Set `TMPPREFIX` and override `mktemp` to use the job-local writable `tmp/`; the device `/tmp` is read-only and the system `mktemp` ignores `TMPDIR`.

## Knowledge Drafts And B-Class Evidence

The adaptation is a B-class candidate despite being a single-file Perl CLI,
because the true-device pass depended on solving several non-obvious runtime
and CI boundary issues:

- `knowledge_drafts/DRAFT-mysqltuner-ohos-perl-runenv-prove.{md,kv}`:
  `prove` exists in `perl/5.42.2`, but direct execution hits the packaged
  shebang and relocated `@INC`; the durable recipe pattern is `perl -S prove`
  under `conanrun`.
- `knowledge_drafts/DRAFT-mysqltuner-shadow-ci-readonly-tmp.{md,kv}`:
  manual isolated shadow CI can exit silently after the L0 banner because the
  device `/tmp` is read-only and system `mktemp` ignores `TMPDIR`; use
  job-local `TMPDIR`, `TMPPREFIX`, and a shell-local `mktemp -p` wrapper.
- `knowledge_drafts/DRAFT-mysqltuner-source-url-fallback.{md,kv}`:
  single GitHub URL timed out on device; the recipe now uses a SHA-checked
  mirror fallback list and still keeps the official GitHub archive as source
  identity.
- `knowledge_drafts/DRAFT-mysqltuner-test-boundary-mysqladmin.{md,kv}`:
  `tests/cli_validation.t` looked like a no-service CLI test but contains an
  authentication path requiring `mysqladmin`/`mariadb-admin`; it was correctly
  deferred instead of smuggling database-client dependencies into this PR.
- `knowledge_drafts/DRAFT-mysqltuner-hmdfs-direct-exec-l2.{md,kv}`:
  L2 direct `--help` smoke is non-blocking on the hmdfs Conan cache, while the
  real consumer proof is interpreter-explicit execution through Conan
  VirtualRunEnv plus L1e destructive negative test.

## Next True-Device/Shadow CI Commands

```sh
CI_PACKAGES="archives/m/mysqltuner/2.9.1" zsh ci/conan/build_and_test.sh
```

Suggested isolated job shape:

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job mysqltuner-2.9.1-$(date +%Y%m%d-%H%M%S) \
  --package archives/m/mysqltuner/2.9.1 \
  --repo-source <existing-repo>

sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

If running manually without the helper-generated runner, initialize the isolated Conan home first and avoid `/tmp`:

```sh
export CONAN_HOME="$HOME/ohos-users/codex/<job>/conan-home"
export TMPDIR="$HOME/ohos-users/codex/<job>/tmp"
export TMPPREFIX="$TMPDIR/zsh"
export CI_PACKAGES="archives/m/mysqltuner/2.9.1"
zsh -c 'mktemp() { command mktemp -p "$TMPDIR" "$@"; }; . ./ci/conan/setup.sh'
zsh -c 'mktemp() { command mktemp -p "$TMPDIR" "$@"; }; . ./ci/conan/build_and_test.sh'
```
