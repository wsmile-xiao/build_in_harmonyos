# dasel

**Display**: dasel  
**Category**: network  
**Homepage**: https://github.com/TomWright/dasel  
**License**: MIT  

Query and modify data structures using selector strings. Supports JSON, YAML, TOML, XML, and CSV formats.

## Overview

dasel (Data Selector) is a command-line tool for querying and modifying data structures using selector strings. It can read, write, and convert between JSON, YAML, TOML, XML, and CSV formats. Similar to jq/yq but with a unified selector syntax across all formats.

## Build System

- **System**: custom (Go build)
- **Compiler**: Go 1.26.3 + clang (CGO_ENABLED=1)
- **Version injection**: `-ldflags="-s -w -X github.com/tomwright/dasel/v2/internal.Version=v2.8.1"`

## Versions

| Version | Status | Date |
|---------|--------|------|
| 2.8.1-r14 | published | 2026-06-02 |