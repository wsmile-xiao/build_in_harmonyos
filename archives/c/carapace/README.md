# carapace

A multi-shell completion library for Go.

## Description
carapace is a Go library for creating shell completions. It supports multiple shells including bash, zsh, fish, elvish, nushell, powershell, and others. The library provides a declarative API for defining completion specifications.

## Version
- Latest compiled: 1.11.7

## Build Notes
- Build system: custom (Go language)
- Go linker mmap is restricted on HongMeng; used upstream pre-built binaries
- Binaries: carapace, carapace-nonposix (both static, CGO_ENABLED=0)

## Dependencies
- Go 1.24+ (build dependency)

## Links
- Source: https://github.com/carapace-sh/carapace
- Website: https://carapace.sh/
