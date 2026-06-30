# crosstool-ng

Crosstool-NG is a versatile (cross) toolchain generator, supporting many architectures and components.

## Overview

Crosstool-NG aims at building toolchains for various architectures and operating systems. It is a Make wrapper that orchestrates the download, configuration, and build of cross-compilation toolchains.

## Key Features

- Supports multiple architectures (ARM, MIPS, PowerPC, x86, etc.)
- Configurable toolchain components (GCC, binutils, libc, etc.)
- Generates toolchains for Linux and other operating systems
- Used for embedded system development

## Compiled Versions

| Version | Status | Date |
|---------|--------|------|
| 1.28.0 | built | 2026-06-02 |

## Usage

```bash
# Install crosstool-ng
ct-ng --version

# Build a cross-compilation toolchain
ct-ng menuconfig
ct-ng build
```

## Official Resources

- Homepage: https://crosstool-ng.github.io/
- Documentation: https://crosstool-ng.github.io/docs/
- GitHub: https://github.com/crosstool-ng/crosstool-ng