# pug 0.6.5 OpenHarmony notes

## Summary

- Package: `pug/0.6.5`
- Upstream: `leg100/pug`, tag `v0.6.5`
- Build system: Go module
- Package output: `bin/pug`

## Build

The recipe builds with `CGO_ENABLED=0`, `GOOS=linux`, and `GOARCH=arm64`. The
release version is injected with
`-X github.com/leg100/pug/internal/version.Version=0.6.5`, matching the
upstream GoReleaser configuration.

For OHOS runners, the Go workspace, module cache, temp directory, and linker
output are routed to `/data/storage/el2/base/*`. Produced ELF files are signed
with `binary-sign-tool`.

## Tests

The upstream release source contains 132 `Test*` functions. This adaptation
runs the CI-safe short Go unit suite: 68 non-integration `Test*` functions are
compiled to signed test binaries and executed directly. `TestConfig` uses
`testing.TempDir`; with the OHOS Go runtime it still attempts `/tmp` even when
`TMPDIR` points at ext2 storage, so it is explicitly excluded. The adapted
suite runs the remaining 67 non-integration tests. The upstream fixture scripts
that use `#!/usr/bin/env bash` are switched to `sh` inside the copied OHOS Go
workspace because the runner does not provide `bash`. The 64
`internal/integration` tests are not run in ordinary CI because upstream's
integration setup requires `mirror/mirror.tfrc`, Terraform provider mirror
data, and external Terraform/Terragrunt/Infracost tools.

Latest OHOS validation:

- Run: `ohos-test-runs/codex-a-0.6.5-pug-0.6.5-20260810-r1-conan-20260810-183218-20092`
- Upstream short Go suite: 67 passed, 0 failed, 0 skipped, 1 excluded
- L0/L1/L2/L4/L5: passed

The `test_package` verifies the packaged executable by running
`pug --version` and checking the `0.6.5` version string.
