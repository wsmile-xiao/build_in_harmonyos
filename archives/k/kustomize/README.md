# kustomize

Kubernetes native configuration management tool.

## Description

kustomize is a tool for customizing Kubernetes YAML configurations without templates. It allows you to define, manage, and apply configuration overlays to Kubernetes resources.

## Features

- Template-free customization of Kubernetes configs
- Native Kubernetes configuration management
- Supports overlays, patches, and generators
- Integrates with kubectl

## Installation

### Precompiled Package

Download the precompiled package for HarmonyOS aarch64:

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- kustomize 5.8.1
```

### Manual Installation

The binary is installed to `~/usr/local/bin/kustomize`.

## Usage

```bash
# Build resources
kustomize build ./path/to/kustomization

# Apply to cluster
kustomize build ./path/to/kustomization | kubectl apply -f -

# Version check
kustomize version
```

## Requirements

- Go 1.24+ (for compilation)
- HarmonyOS/OpenHarmony aarch64

## Version History

| Version | Status | Date |
|---------|--------|------|
| 5.8.1 | built | 2026-05-13 |

## License

Apache-2.0

## Source

https://github.com/kubernetes-sigs/kustomize