# DRAFT-mysqltuner-shadow-ci-readonly-tmp - manual shadow CI on OHOS can fail silently when /tmp is read-only

- Trigger event: mysqltuner 2.9.1 manual isolated shadow CI
- Path: Path B knowledge extension
- Phase: L0 preflight / CI script execution

## Symptom

The targeted CI command printed only:

```text
[step] L0: Quality gate checks...
```

and exited with code 1. No L0 failure detail was printed.

Direct probing on the same device showed:

```text
mktemp: Failed to create file /tmp/tmp.XXXXXXXXXX: Read-only file system
```

The shell also failed to create here-doc temporary files under `/tmp`.

## Root Cause

The manual isolated job had a writable job-local `tmp/`, but the device's
system `mktemp` ignored `TMPDIR` unless `-p` was passed. zsh here-doc handling
also needed `TMPPREFIX` to avoid `/tmp`. Because the CI script runs with
`set -euo pipefail`, `mktemp` failure inside L0 aborted the script before the
diagnostic branch could print a structured failure.

## Fix For Manual Shadow CI

Do not patch repository CI scripts in a package PR. For manual isolated runs,
wrap the shell invocation so temporary files stay inside the job-local tmp:

```sh
export TMPDIR="$HOME/ohos-users/codex/<job>/tmp"
export TMPPREFIX="$TMPDIR/zsh"
zsh -c 'mktemp() { command mktemp -p "$TMPDIR" "$@"; }; . ./ci/conan/setup.sh'
zsh -c 'mktemp() { command mktemp -p "$TMPDIR" "$@"; }; . ./ci/conan/build_and_test.sh'
```

## Verification

With `TMPPREFIX` and the local `mktemp` wrapper, the same mysqltuner job passed
L0, configured the registry through setup, downloaded `perl/5.42.2`, built the
package, and completed shadow CI with exit 0.

## Reuse

When an OHOS PC shadow-CI run stops immediately after a step banner and the log
contains no package failure, probe temporary-file creation before changing the
recipe. The failure may be a runner environment issue, not a package issue.
