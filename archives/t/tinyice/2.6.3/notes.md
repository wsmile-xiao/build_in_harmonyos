# tinyice 2.6.3 adaptation notes

## Scope

- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1697
- Upstream: https://github.com/DatanoiseTV/tinyice
- Release: https://github.com/DatanoiseTV/tinyice/releases/tag/v2.6.3
- Package path: `archives/t/tinyice/2.6.3`

## W0 dependency check

- Conan `requirements()`: none.
- Conan `tool_requirements()`: none; the registry still has no compatible
  Go package for this source requirement.
- Upstream source is a Go module (`go.mod`, Go 1.25.1) with many module dependencies resolved by the Go toolchain during `go build`.
- The recipe downloads the official v2.6.3 source archive and builds the CLI from source.
- Device-side probing showed pre-existing `$HOME/.local/bin/go` was not
  executable and no compatible `go/*` recipe was available in the registry.
  The recipe now probes installed Go executables first and otherwise downloads
  a pinned Go 1.26.3 host archive. The archive is selected for the build
  machine architecture and verified by SHA-256 before extraction.
- On OHOS, the fallback toolchain is placed on writable non-HMDFS storage and
  every ELF under `bin/` and `pkg/tool/linux_<arch>/` is self-signed before
  `go version` or `go build` is executed. This is a build-only toolchain and is
  not included in the tinyice package.
- No runtime Conan library dependencies are introduced, so there is no dependency library to split into a separate issue/PR.

## 依赖

- Conan dependencies: none.
- Tool requirements: none declared because the package registry has no
  compatible Go recipe. A compatible installed Go is reused when available;
  otherwise the recipe bootstraps the pinned, checksum-verified Go 1.26.3
  archive described in `conandata.yml`.
- Upstream Go module dependencies are handled by Go modules during the source build.

## Source and build-system analysis

- Upstream build system: Makefile wrapping Go commands.
- `make build` runs `go generate ./server/...` and `go build -o tinyice .`.
- `make quick` runs `go build -o tinyice .`.
- Upstream test command is `go test ./...`.
- Fresh source scan of the official v2.6.3 archive found 84 top-level `func Test...` declarations, mainly under `relay/` and `server/`.

The recipe uses the repository's existing Go application adaptation pattern: build a linux/arm64 Go binary from the official source archive, then verify it on HarmonyOS through `test_package`.

## Packaging strategy

- Download official v2.6.3 source archive.
- Build `tinyice-real` from source with a usable Go toolchain and `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build`.
- Route the fallback toolchain, `GOCACHE`, `GOMODCACHE`, `GOPATH`,
  `GOTMPDIR`, `TMPDIR`, and the final Go linker output through
  `/data/storage/el2/base/cache`, `/data/storage/el2/base/haps/entry/files`,
  or another explicitly configured writable root. This avoids the known HMDFS
  `mmap MAP_SHARED` failure mode seen by other Go packages.
- Install the real binary as `libexec/tinyice/tinyice-real`.
- Self-sign the real binary on OHOS with `binary-sign-tool` so the kernel can load it.
- Build and install `bin/tinyice` as a tiny OHOS-native C wrapper using the C compiler from Conan `tools.build:compiler_executables`.
- The wrapper resolves `tinyice-real` relative to its own installed path and forwards all invocations.

## Validation

- `test_package` verifies the real binary is an AArch64 ELF.
- `test_package` runs both the packaged wrapper and `tinyice-real` with `--help` when `can_run(self)` is true, so L2 verifies that the signed real binary loads on the target instead of checking a wrapper-owned string.
- AI Review follow-up on 2026-08-02 confirmed the old hard-coded `--version` wrapper masked a real `Permission denied` failure from an unsigned binary. The recipe now self-signs `tinyice-real` with `binary-sign-tool`.
- Local HarmonyOS validation was rerun on a HarmonyOS real device with a temporary, self-signed Go 1.25.1 toolchain.
- Direct `go test ./...` on HarmonyOS linked successfully only when Go output was placed under `/data/storage/el2/base/cache`, but then failed to execute the generated unsigned test binaries. The validation therefore used `go test -c` for `./relay` and `./server`, self-signed the generated `relay.test` and `server.test` ELF files, and executed them in their source directories.
- Upstream validation result: 84/84 top-level tests passed, 0 failed, 0 skipped. The signed test-binary logs emitted 94 `RUN` records including subtests, all passing.
- `conan-build-test` validation result: PASS. The run built `tinyice-real` from source, self-signed it, packaged the wrapper, executed `test_package`, passed L1 negative sabotage, and passed L2 `tinyice --help`.
- Official PR CI must be rerun after this patch. The prior public CI reached
  `build()` and failed because the worker did not provide a usable `go` in
  `PATH`; the recipe now handles that exact condition by bootstrapping the
  pinned toolchain, signing it on OHOS, and verifying `go version` before the
  source build.
- Runtime coverage is intentionally limited to CLI loadability and packaging. Full TinyIce streaming behavior (RTMP/SRT/WebRTC/HLS serving paths) still requires manual functional validation.

## 验证结果

```bash
# Real-device upstream test verification used a temporary, self-signed Go 1.25.1 toolchain.
export VALIDATION_ROOT=$HOME/validation/tinyice-pr3797
export GO_TOOL=$VALIDATION_ROOT/.toolchains/go1.25.1/go
export PATH=$GO_TOOL/bin:/data/service/hnp/bin:$HOME/.local/bin:$HOME/usr/local/bin:$PATH
export GOROOT=$GO_TOOL
export GOTOOLCHAIN=local
export GOPROXY=https://goproxy.cn,direct
export TMPDIR=/data/storage/el2/base/cache/tinyice-pr3797-signed/tmp
export GOTMPDIR=$TMPDIR
export GOCACHE=/data/storage/el2/base/cache/tinyice-pr3797-signed/gocache
export GOMODCACHE=$VALIDATION_ROOT/.tmp/gomodcache

# Build upstream test binaries, self-sign them, and run them on OHOS.
go test -c -o /data/storage/el2/base/cache/tinyice-pr3797-signed/relay.test ./relay
binary-sign-tool sign -inFile /data/storage/el2/base/cache/tinyice-pr3797-signed/relay.test -outFile /data/storage/el2/base/cache/tinyice-pr3797-signed/relay.test.signed -selfSign 1
mv /data/storage/el2/base/cache/tinyice-pr3797-signed/relay.test.signed /data/storage/el2/base/cache/tinyice-pr3797-signed/relay.test
(cd relay && /data/storage/el2/base/cache/tinyice-pr3797-signed/relay.test -test.v -test.count=1 -test.timeout=20m)

go test -c -o /data/storage/el2/base/cache/tinyice-pr3797-signed/server.test ./server
binary-sign-tool sign -inFile /data/storage/el2/base/cache/tinyice-pr3797-signed/server.test -outFile /data/storage/el2/base/cache/tinyice-pr3797-signed/server.test.signed -selfSign 1
mv /data/storage/el2/base/cache/tinyice-pr3797-signed/server.test.signed /data/storage/el2/base/cache/tinyice-pr3797-signed/server.test
(cd server && /data/storage/el2/base/cache/tinyice-pr3797-signed/server.test -test.v -test.count=1 -test.timeout=20m)
```

Result: upstream signed test binaries passed 84/84 top-level tests on HarmonyOS. Detailed logs are retained in the validation workspace and can be provided to reviewers on request.

```bash
cd $VALIDATION_ROOT/build_in_harmonyos
export GO_TOOL=$VALIDATION_ROOT/.toolchains/go1.25.1/go
export PATH=$GO_TOOL/bin:/data/service/hnp/bin:$HOME/.local/bin:$HOME/usr/local/bin:$PATH
export GOROOT=$GO_TOOL
export GOTOOLCHAIN=local
export GOPROXY=https://goproxy.cn,direct
export TMPDIR=/data/storage/el2/base/cache/tinyice-pr3797-conan/tmp
export TMPPREFIX=$TMPDIR/tinyice
export TINYICE_GO_TMPDIR=/data/storage/el2/base/cache/tinyice-pr3797-conan/go-output
export GOMODCACHE=$VALIDATION_ROOT/.tmp/gomodcache
export CONAN_HOME=$VALIDATION_ROOT/.conan2-tinyice-go1251
export CI_PACKAGES=archives/t/tinyice/2.6.3
zsh -f ci/conan/build_and_test.sh
```

Result: `conan-build-test` passed on HarmonyOS. The run reported L0/L1/L2/L4/L5 all pass and `test_package` executed successfully. Detailed logs are retained in the validation workspace and can be provided to reviewers on request.

## Closure

Current status: tinyice 2.6.3 recipe, upstream test verification, and
`test_package` smoke validation passed on the HarmonyOS device. Official CI
still needs a rerun for the new self-bootstrap path; a preinstalled Go is no
longer required. Full media-streaming scenario validation remains outside this
package smoke scope.

## Knowledge extension

The reusable upstream-test migration pattern is recorded as a draft rather than modifying the formal graph directly:

- `knowledge/drafts/E318-draft-XGW1.kv`
- `knowledge/drafts/E318-draft-XGW1.md`

The draft captures the separation of `go test` into package-level `go test -c`, non-HMDFS output, ELF self-signing, and execution from the original package source directory. It is backed by the 84/84 upstream test result above and remains `draft: true` for editor review.
