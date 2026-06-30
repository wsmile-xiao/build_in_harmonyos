# kubelogin

A kubectl plugin for Kubernetes OIDC authentication (also known as `kubectl-oidc_login`).

## Description

kubelogin is a Go-based kubectl credential plugin that implements OIDC authentication for Kubernetes clusters.
It provides a browser-based login flow and token management for OIDC-enabled Kubernetes API servers.

- **Homepage**: https://github.com/int128/kubelogin
- **License**: Apache-2.0
- **Category**: kubernetes/cli
- **Build system**: custom (Go)

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 1.36.2 | published | 2026-06-01 |

## Binary Names

- `kubectl-oidc_login` (primary binary name per kubectl plugin convention)

## Usage

```bash
kubectl oidc-login --version
# kubelogin version 1.36.2
```