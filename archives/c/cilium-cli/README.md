# cilium-cli

Cilium CLI tool for installing, managing, and troubleshooting Cilium (Kubernetes CNI plugin).

## Overview

cilium-cli is the command-line interface for Cilium, an open source networking, observability, and security solution for Kubernetes using eBPF. It provides capabilities to:
- Install and configure Cilium on Kubernetes clusters
- Check cluster connectivity status
- Enable and manage Hubble observability
- Troubleshoot networking issues

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| v0.19.4 | built | CGO_ENABLED=0 static Go build, requires Go >= 1.26.0 |

## Build Requirements

- Go >= 1.26.0 (project uses Go 1.26 std packages: crypto/pbkdf2, crypto/hkdf, crypto/sha3, weak)
- Binary name: `cilium` (build target: ./cmd/cilium)

## Usage

```bash
cilium version
cilium install
cilium connectivity test
cilium hubble enable
cilium status
```
