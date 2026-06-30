# yamlfmt

yamlfmt is a simple command line tool for formatting YAML files.

It is a Go-based tool that reads YAML input, formats it according to configurable rules, and outputs the formatted YAML.

## Key Features
- Simple command line interface
- Configurable formatting rules
- Supports doublestar glob patterns for file selection
- Stdin/stdout support

## Build Requirements
- Go 1.26.0 (required due to HMDFS mmap compatibility)
- CGO_ENABLED=0

## Platform Notes
- Go linker on HMDFS requires Go 1.26.0+ (older versions have mmap permission denied issues)
- All binaries need ELF signing on HarmonyOS
