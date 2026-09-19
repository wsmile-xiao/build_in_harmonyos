# kubeconform

**Display**: kubeconform
**Category**: network
**Homepage**: https://github.com/yannh/kubeconform
**License**: Apache-2.0

A FAST Kubernetes manifests validator, with support for Custom Resources.

## Overview

Kubeconform validates Kubernetes manifests against JSON schemas (default registry
is a fork of kubernetes-json-schema, plus local `-schema-location` support for
offline validation and CRDs). Pure-Go CLI tool, built here with `-mod=vendor`
fully offline.

## Build System

- **System**: custom (Go build)
- **Compiler**: Go 1.24.0, CGO_ENABLED=0
- **Version injection**: `-ldflags="-s -w -X main.version=v0.7.0"`
- **Upstream tests**: `go test -mod=vendor -v ./...` (12 files, 20 Test funcs)

## Versions

| Version | Status | Date |
|---------|--------|------|
| 0.7.0 | built | 2026-09-18 |
