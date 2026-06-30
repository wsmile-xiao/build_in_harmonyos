# redo

**Smaller, easier, more powerful, and more reliable than make.**

## Description

redo is an implementation of Daniel J. Bernstein's redo build system. He never released his version, so other people have implemented different variants based on his published specification.

This version, sometimes called apenwarr/redo, is probably the most advanced one, including parallel builds, improved logging, extensive automated tests, and helpful debugging features.

## Homepage

- GitHub: https://github.com/apenwarr/redo
- Documentation: https://redo.rtfd.io

## Features

- **Recursive build system**: Tracks dependencies automatically
- **Parallel builds**: Supports concurrent compilation with -j option
- **Improved logging**: Better debugging and monitoring capabilities
- **Extensive testing**: Comprehensive automated test suite
- **Shell compatibility**: Works with multiple shell implementations (bash, zsh, etc.)

## Compiled Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 0.42d   | published | 2026-06-18 |

## Build Configuration

- **Build System**: redo (./do)
- **Language**: Python
- **Dependencies**: Python 3.x, shell (bash/zsh)
- **Platform**: HongMeng Kernel 1.12.0

## Installation

Precompiled packages available through cmd-pkgs:

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- redo 0.42d
```

## Usage

After installation, redo commands are available:

```bash
redo           # Build default target
redo -j4 all   # Parallel build
redo test      # Run tests
redo clean     # Clean build artifacts
```

## License

Apache License 2.0

## References

- Original specification: http://cr.yp.to/redo.html
- Mailing list: redo-list@googlegroups.com