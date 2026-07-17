# flash Homebrew Adaptation Notes

## Build Strategy

The Homebrew formula for `flash` packages upstream release `2.7.2` as a single
Bash script. The Conan recipe downloads that script, installs it to `bin/flash`,
and marks it executable. No native compiler or generated build system is needed.

## OHOS Notes

- The upstream shebang already uses `/usr/bin/env bash`.
- Runtime flashing operations may need platform disk utilities and elevated
  permissions. The package does not execute those destructive paths in CI.
- The smoke test is intentionally non-destructive: it checks `--version` and
  `--help` behavior only.

## Verification

Local verification covers Python syntax, archive metadata, and L0 structure.
Remote OHOS CI must run the Conan `test_package` before this PR can move to B1.
