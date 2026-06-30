# doggo - Command-line DNS Client for Humans

## Overview

**doggo** is a modern command-line DNS client written in Golang. It's a replacement for traditional tools like `dig`, with a focus on human-readable output and modern DNS features.

## Key Features

- **Human-readable output**: Clean, colored, tabular format
- **Multiple protocols**: DoH (DNS over HTTPS), DoT (DNS over TLS), DoQ (DNS over QUIC), DNSCrypt
- **JSON output**: Easy scripting and parsing
- **EDNS support**: Client Subnet (ECS), NSID, Cookies, Padding
- **Internationalized Domain Names**: Automatic punycode conversion
- **Reverse DNS lookups**: PTR record queries
- **Globalping integration**: Test DNS from multiple locations worldwide

## Installation

Use the cmd-pkgs installer:

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- doggo 1.1.2-r5
```

## Usage Examples

```bash
# Simple DNS lookup
doggo example.com

# Query MX records
doggo MX github.com @9.9.9.9

# Use DNS over HTTPS
doggo example.com @https://cloudflare-dns.com/dns-query

# JSON output
doggo example.com --json

# Reverse DNS lookup
doggo --reverse 8.8.8.8
```

## Dependencies

- **Go 1.26.0+**: Required for compilation (static binary, no runtime dependencies)
- **No external libraries**: All dependencies are embedded in the static binary

## OpenHarmony Adaptation

- Compiled with `CGO_ENABLED=0` for pure static linking
- ELF signed for execution permission
- No platform-specific patches required
- Full functionality available on OpenHarmony

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 1.1.2-r5 | 2026-05-29 | published | Initial OpenHarmony build |

## Source

- GitHub: https://github.com/mr-karan/doggo
- Version: v1.1.2

## License

MIT License