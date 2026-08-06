# tektoncd-cli

Command-line interface for interacting with Tekton.

## Version

- 0.45.0.1

## Build notes

- Packages the upstream linux/aarch64 release archive published by Tekton.
- Avoids requiring a Go toolchain on the OHOS CI worker, which currently does not provide `go`.
- Installs the `tkn` executable to `bin/`.

## Test notes

The Conan `test_package` verifies the installed executable exists and, when runnable, checks `tkn --help` and `tkn version`.
