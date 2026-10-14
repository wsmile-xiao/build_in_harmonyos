# kustomizer

An experimental package manager for distributing Kubernetes configuration as
OCI artifacts. It offers commands to publish, fetch, diff, customize, validate,
apply and prune Kubernetes resources.

- Upstream: https://github.com/stefanprodan/kustomizer
- Version: 2.2.1
- License: Apache-2.0
- Language / build system: Go (pure-Go static binary, `CGO_ENABLED=0`)

## HarmonyOS PC (aarch64) adaptation

The recipe bootstraps the official static Go toolchain (`go1.24.13`,
sha256-verified against the go.dev release manifest) inside the Conan build
folder, because neither the CI runners nor the `ohpcd` registry provide a Go
toolchain. `kustomizer` is then compiled as a fully static aarch64 binary and
self-signed with the HarmonyOS `binary-sign-tool` so it can be executed on the
device.

All 15 upstream top-level test functions (37 subtests) pass against a local
[envtest](https://book.kubebuilder.io/reference/envtest.html) control plane; see
`2.2.1/reports/upstream-test-ledger.md` for the full ledger.
