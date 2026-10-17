# kubeaudit

**Display**: kubeaudit
**Category**: network
**Homepage**: https://github.com/Shopify/kubeaudit
**License**: MIT

A Kubernetes security auditor that checks clusters and manifests against
security best practices (Shopify). Pure-Go CLI tool, built here with
`CGO_ENABLED=0` and the module closure fetched through GOPROXY (upstream has
no vendor/ directory).

## Overview

kubeaudit audits Kubernetes manifests (`-f` manifest mode, fully offline) and
clusters (cluster/local modes) for common security controls: privileged
containers, capability abuse, AppArmor/seccomp, runAsNonRoot, hostPath
mounts, network policies, image tags, resource limits and deprecated API
versions. It can also auto-fix supported findings (`autofix`).

## Build System

- **System**: custom (Go build)
- **Compiler**: Go 1.24.0 (go.mod requires >= 1.22.1), CGO_ENABLED=0
- **Module mode**: `-mod=mod` + GOPROXY (goproxy.cn), GOTOOLCHAIN=local
- **Version injection**: `go:embed cmd/commands/VERSION` (upstream ldflags
  `-X` targets are vestigial; fixed values injected for Makefile parity)
- **Upstream tests**: `go test -mod=mod ./...` (37 files, 21 packages, 64
  top-level Test funcs; manifest mode offline, cluster mode self-skips)

## Versions

| Version | Status | Date |
|---------|--------|------|
| 0.22.2 | built | 2026-09-23 |
