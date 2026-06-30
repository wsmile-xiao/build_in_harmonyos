# ripgrep

ripgrep is a line-oriented search tool that recursively searches your current directory for a regex pattern. By default, ripgrep will respect your .gitignore and automatically skip hidden files/directories and binary files.

## Description

ripgrep (rg) is a high-performance search tool similar to grep, but with better performance and more features:
- Built on Rust's regex engine for high performance
- Automatically respects .gitignore files
- Skips hidden files and directories by default
- Supports multiple search patterns
- Built-in support for various file encodings
- SIMD acceleration (NEON on ARM)

## Versions

| Version | Status | Build Date | Notes |
|---------|--------|------------|-------|
| 15.1.0 | built | 2026-05-22 | First successful compile for OpenHarmony |

## Features

ripgrep 15.1.0 features:
- SIMD acceleration: +NEON (compile and runtime)
- No PCRE2 support (not available in this build)
- High performance regex search
- Automatic .gitignore support
- Multiple encoding support

## Build Information

### Build System
- **Type**: cargo (Rust)
- **Compiler**: rustc 1.95.0, cargo 1.95.0

### Dependencies
- Rust toolchain (rustc, cargo)
- SSL certificates for crates.io index download

### Build Configuration
- Build type: release (optimized)
- SIMD: NEON (compile and runtime)
- Features: -pcre2 (PCRE2 not available)

## Usage

```bash
# Search for a pattern in current directory
rg "pattern"

# Search in specific directory
rg "pattern" /path/to/directory

# Search with context lines
rg -C 3 "pattern"

# Search only specific file types
rg -t rust "pattern"

# Show version
rg --version
```

## OpenHarmony Compatibility

ripgrep 15.1.0 has been successfully compiled and tested on OpenHarmony:
- Binary integrity verified (G1 PASS)
- Functional tests passed (G2 PASS)
- Portability verified (G3 PASS - no RPATH needed for Rust static binary)
- Archive integrity verified (G4 PASS)

## References

- Official repository: https://github.com/BurntSushi/ripgrep
- Official documentation: https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md