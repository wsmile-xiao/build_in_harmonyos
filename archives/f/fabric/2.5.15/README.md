# fabric 2.5.15

Hyperledger Fabric core — official linux-arm64 binaries, packaged for Conan.

## Description

This Conan package ships the **official, upstream-pre-compiled** Hyperledger
Fabric v2.5.15 linux-arm64 binaries. It is a **binary-packaging** recipe — no
source compilation is performed.

### Why binary packaging?

fabric is a Go project. The OpenHarmony/HarmonyOS PC build environment this
skill targets has **no Go toolchain** (the `go` binary is permission-denied
and the CI-capability matrix lists Go as unavailable). Upstream therefore
publishes official linux-arm64 binary tarballs on every release; this recipe
downloads and repackages that official artifact via Conan.

## Binaries shipped

The tarball contains 8 static arm64 ELF executables in `bin/`:

| Binary | Purpose |
|--------|---------|
| `peer` | Fabric peer node CLI |
| `orderer` | Ordering service node |
| `configtxgen` | Channel config transaction generator |
| `configtxlator` | Config protobuf ↔ human-readable translator |
| `cryptogen` | Crypto material generator |
| `discover` | Service discovery CLI |
| `ledgerutil` | Ledger compare/diff utility |
| `osnadmin` | Orderer admin CLI |

Plus `config/` (`orderer.yaml`, `configtx.yaml`, `core.yaml`) and
`builders/ccaas/` chaincode-builder scripts.

## Usage

```bash
conan install --requires=fabric/2.5.15
# binaries land in <package>/bin/
${bin}/peer version
```

## Source / checksum

- URL: https://github.com/hyperledger/fabric/releases/download/v2.5.15/hyperledger-fabric-linux-arm64-2.5.15.tar.gz
- SHA256: `7ff43e19f8df6ad9f3c5a8bd9b5567c4686d626d0abad0b3c15ae7ff84fdcc03`

## Platform support

- `settings.os` ∈ {Linux, OHOS} (R32)
- `settings.arch` ∈ {armv8, aarch64}
- Only linux-arm64 is packaged; other (os, arch) → `ConanInvalidConfiguration`.

## License

Apache-2.0
