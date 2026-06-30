# massdns

High-performance DNS stub resolver for bulk DNS lookups.

## Description

MassDNS is a simple high-performance DNS stub resolver targeting those who seek to resolve a massive amount of domain names in the order of millions or even billions. It is designed to be extremely fast and efficient.

## Features

- High-performance DNS resolution
- Supports batch processing of domain names
- IPv4 and IPv6 support
- Customizable DNS servers

## Usage

```bash
massdns -r resolvers.txt domains.txt -o S -w results.txt
```

## Versions

- 1.1.0 (2026-06-04) - Built for OpenHarmony aarch64

## Links

- GitHub: https://github.com/blechschmidt/massdns
- Savannah: https://download.savannah.nongnu.org/releases/massdns/