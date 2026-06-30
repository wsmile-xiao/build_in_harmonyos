# kyverno

Kyverno is a Kubernetes-native policy engine. It enables policy enforcement, mutation, and generation for Kubernetes resources using Kubernetes-native declarative policies (CRDs).

## Binaries

- **kyverno**: The main policy controller that runs inside a Kubernetes cluster
- **kyverno-cli**: The CLI tool (kubectl-kyverno) for policy testing and management

## Version

- 1.13.0

## Build System

- Go (CGO_ENABLED=0, pure Go binary, statically linked)