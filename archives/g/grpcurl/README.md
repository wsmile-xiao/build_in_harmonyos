# grpcurl

Like cURL, but for gRPC: a command-line tool that lets you interact with gRPC servers.

## Overview

grpcurl is a command-line tool for interacting with gRPC servers, similar to how curl interacts with HTTP servers. It supports gRPC server reflection and proto file definitions for service discovery and method invocation.

## Homebrew Info

- Homebrew Formula: grpcurl (#485)
- Installs: 8302 (365 days)
- License: MIT
- Homepage: https://github.com/fullstorydev/grpcurl

## OpenHarmony Compilation

### Version 1.9.3
- **Build System**: Go
- **Compiler**: Go 1.22.10 (CGO_ENABLED=0, static binary)
- **Status**: built
- **Key Challenges**: 
  - Go PIE/DYN binary signing corrupts TLS program header
  - Static binary (EXEC type) works with binary-sign-tool
  - Go 1.23+ DIT ARM64 assembly unsupported on OpenHarmony

### Build Command
```bash
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
go build -ldflags "-s -w -X main.version=1.9.3" \
-o grpcurl ./cmd/grpcurl/
```

### Signing
```bash
binary-sign-tool sign -inFile grpcurl -outFile grpcurl_signed -selfSign 1
```
