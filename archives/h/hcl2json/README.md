# hcl2json

Convert HCL (HashiCorp Configuration Language) to JSON.

## Description

hcl2json is a command-line tool that converts HCL format files to JSON format. It is commonly used with Terraform configurations, allowing HCL files to be processed by tools that expect JSON input.

## Source

- **Repository**: https://github.com/tmccombs/hcl2json
- **Language**: Go
- **Build System**: Custom (Go build)

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 0.6.9 | built | 2026-06-18 |

## Usage

```bash
hcl2json [file.hcl]
hcl2json --version
hcl2json -simplify [file.hcl]
```

## Build Notes

- Pure Go project, compiled with `CGO_ENABLED=0` for static linking
- Compatible with HarmonyOS/OpenHarmony arm64 architecture
