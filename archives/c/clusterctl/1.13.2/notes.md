# clusterctl 1.13.2 Build Notes

## Build Method
- Compiled from source using Go 1.26.4 (CGO_ENABLED=0 for static binary)
- Target: linux/arm64 (OpenHarmony aarch64/musl compatible)
- Prebuilt binary was also downloaded but could not execute on OpenHarmony (permission denied)
- Source compilation with `go install` succeeded

## Build Command
```bash
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go install -trimpath \
  -ldflags "-X 'sigs.k8s.io/cluster-api/version.gitVersion=v1.13.2' \
  -X 'sigs.k8s.io/cluster-api/version.gitMajor=1' \
  -X 'sigs.k8s.io/cluster-api/version.gitMinor=13' \
  -X 'sigs.k8s.io/cluster-api/version.gitCommit=v1.13.2' \
  -X 'sigs.k8s.io/cluster-api/version.gitTreeState=clean' \
  -X 'sigs.k8s.io/cluster-api/version.buildDate=2026-06-12T02:30:07Z' \
  -s -w" \
  sigs.k8s.io/cluster-api/cmd/clusterctl@v1.13.2
```

## Verification
- `$DEFAULT_PREFIX/bin/clusterctl version` → v1.13.2
- Binary: ELF 64-bit LSB arm64, static, stripped (44MB)

## Issues
- Prebuilt binary from GitHub releases could not execute on OpenHarmony (permission denied)
- Required compilation from source with CGO_ENABLED=0 for static musl-compatible binary
- GOPROXY=https://goproxy.cn,direct used for China mirror acceleration
---

**编译结束**: 2026-06-15 11:52
**最终状态**: built
