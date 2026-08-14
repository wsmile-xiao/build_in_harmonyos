# ahoy 2.5.0 OpenHarmony notes

## Summary

- Package: `ahoy/2.5.0`
- Upstream: `ahoy-cli/ahoy`, tag `v2.5.0`
- Build system: Go module under `v2/`
- Package output: `bin/ahoy`

## Build

The recipe builds from `v2/` with `CGO_ENABLED=0`, `GOOS=linux`, and
`GOARCH=arm64`. The release version is injected with `-X main.version=2.5.0`.
On OHOS, the recipe replaces ahoy's hard-coded `bash -c` command runner with
`sh -c`, because the device provides `/bin/sh` but not bash.

For OHOS runners, the Go workspace, module cache, temp directory, and linker
output are routed to `/data/storage/el2/base/*`. Produced ELF files are signed
with `binary-sign-tool`.

## Tests

The upstream Go unit tests are discovered from `go list` and run as signed
test binaries. The upstream inventory in the release source contains 36
`Test*` functions across 4 `_test.go` files. `TestOverrideExample` calls the
CLI path through `appRun` and triggers `os.Exit`, which is not compatible with
direct signed test-binary execution, so it is explicitly excluded. The adapted
suite runs the remaining 35 tests; on the OHOS runner, 28 passed and 7
Windows-specific tests called `t.Skip`.

Latest OHOS validation:

- Run: `ohos-test-runs/codex-a-2.5.0-ahoy-2.5.0-20260810-r1-conan-20260810-165451-49887`
- Upstream Go suite: 28 passed, 0 failed, 7 skipped, 1 excluded
- L0/L1/L2/L4/L5: passed

The `test_package` creates a minimal `.ahoy.yml`, runs `ahoy --version`, and
executes `ahoy -f .ahoy.yml hello` to verify the packaged command runner.
