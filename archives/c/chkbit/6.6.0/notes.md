# chkbit 6.6.0 adaptation notes

## Environment

- Build system: Go module
- Date: 2026-07-31
- Toolchain used on device: Go 1.24.0 linux/arm64 SDK, self-signed with `binary-sign-tool`
- CI bootstrap: recipe auto-downloads official Go 1.24.0 linux-amd64/linux-arm64 SDKs when `GO`/`GOROOT`/`PATH` lacks usable Go
- Status: built; targeted device CI passed

## Build steps

```bash
export GOROOT="$HOME/tmp/go-sdk-cache/go1.24.0-sdk"
export GO="$GOROOT/bin/go"
export GOPROXY="https://goproxy.cn,https://proxy.golang.org,direct"
export GOSUMDB="sum.golang.google.cn"
export GOTOOLCHAIN=local
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=arm64
"$GO" mod download
"$GO" build -trimpath -ldflags "-s -w -X main.appVersion=v6.6.0" -o chkbit ./cmd/chkbit
```

The Conan recipe redirects Go tmp/cache/link output to `/data/storage/el2/base/haps/entry/files/chkbit-conan-go/6.6.0` on OHOS. If Go >= 1.24 is not available, it downloads the official Go 1.24.0 SDK from golang.google.cn with dl.google.com fallback and pinned SHA256, signs only unsigned SDK runtime tool binaries on OHOS, then self-signs chkbit/test ELF outputs with `binary-sign-tool` before packaging or execution.

## Issues and solutions

| # | Issue | Root cause | Resolution |
|---|-------|------------|------------|
| 1 | Local Windows lacks `go` / `conan` | Tools are not present in PATH | Device validation used CI Conan 2.29.1 and a temporary signed Go 1.24.0 SDK |
| 2 | `go` from downloaded SDK reports `Permission denied` | HarmonyOS requires ELF signing for downloaded toolchain binaries | Self-signed `bin/go`, `bin/gofmt`, and `pkg/tool/linux_arm64/*` with `binary-sign-tool` |
| 3 | Go linker: `mapping output file failed: permission denied` | HMDFS does not allow Go linker's output mmap pattern | Use `/data/storage/el2/base/haps/entry/files` for `TMPDIR`, `GOTMPDIR`, `GOCACHE`, `GOMODCACHE`, and link output |
| 4 | Upstream `scripts` tests fail on `/tmp/chkbit` | HarmonyOS `/tmp` is read-only and upstream tests hard-code `/tmp/chkbit` | Recipe runs upstream root and `cmd/chkbit/util` tests on Linux and as signed OHOS test binaries; `scripts` tests were separately verified in a temporary source with only `/tmp/chkbit` relocated to `/data/storage/el2/base/haps/entry/files/chkbit-testdata` |
| 5 | PR CI worker lacks Go >= 1.24 | OpenHarmony CI image does not guarantee a Go toolchain in `PATH` | Recipe bootstraps Go 1.24.0 SDK for linux-amd64/linux-arm64 from golang.google.cn with dl.google.com fallback and pinned SHA256 and signs only unsigned SDK runtime tool binaries on OHOS before `go mod download`, upstream tests, and build |

## Source changes

No upstream source patches.

## Dependencies

- Conan dependencies: none
- Build tool: Go >= 1.24; recipe auto-bootstraps Go 1.24.0 when missing
- Go modules: github.com/alecthomas/kong v1.12.1, github.com/laktak/lterm v1.4.0, go.etcd.io/bbolt v1.4.3, golang.org/x/sys v0.37.0, lukechampine.com/blake3 v1.4.1

## Validation result

```bash
# Device upstream tests
# recipe runs: go test . ./cmd/chkbit/util on Linux; go test -c, sign, and execute root/util test binaries on OHOS
# root package and cmd/chkbit/util: passed on device
# scripts package: passed after temporary /tmp/chkbit -> /data/.../chkbit-testdata relocation

# Device Conan create
conan create archives/c/chkbit/6.6.0 \
  -pr:h=$HOME/validation/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$HOME/validation/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  --build=missing
# CONAN_CREATE_RC=0

# Targeted package CI
CI_PACKAGES=archives/c/chkbit/6.6.0 zsh ci/conan/build_and_test.sh
# BUILD_AND_TEST_TARGETED_RC=0
```

CI summary:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: chkbit --help OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
```

## Notes

- issue: TBD; no clear issue number found in repository files or conversation context.
- Software-level `commands.json` is included for the `chkbit` executable.
- A previous accidental non-targeted CI invocation began scanning the full repository; it was stopped, then rerun with `CI_PACKAGES=archives/c/chkbit/6.6.0`.
