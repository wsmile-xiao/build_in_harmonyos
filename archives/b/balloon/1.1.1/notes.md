# balloon 1.1.1 OHOS Adaptation Notes

## Source
- orig.tar.xz 15380 bytes, sha256 410fd41c0aa143482fe2a2ab312730fef926d3f3bb435e1a46595c0065f83e58
- Provenance: Debian balloon_1.1.1-2, mirrored via mirrors.edge.kernel.org (primary) + deb.debian.org fallback
- Contains: balloon/balloon.go, balloon_test.go, cmd/balloon/main.go, go.mod (go 1.12)

## Build
- Pure Go, no CGO, cross compile with GOOS=linux GOARCH=arm64
- `go test ./...` in source root validates B() and H()
- `go build -trimpath -o balloon ./cmd/balloon` produces CLI

## OHOS Specific
- Go toolchain: use `go` from PATH or /usr/local/go/bin/go; if missing, upstream tests skipped with reason
- Binary signing: sign ELF via binary-sign-tool after install (like other binaries)

## Verification
- Upstream tests: 2 discovered (TestB, TestH), executed via `go test -v ./...`
- Test package: Go program importing balloon.B / balloon.H + CLI help check
