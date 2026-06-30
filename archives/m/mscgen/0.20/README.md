# mscgen 0.20 — OpenHarmony aarch64

Message Sequence Chart Generator, compiled for OpenHarmony aarch64.

## Build Configuration

- **Build system**: autotools (configure + make)
- **Configure options**: `--without-png` (libgd not available on target)
- **Compiler**: clang/clang++
- **Target**: aarch64 (musl libc)

## Output Formats

- ✅ SVG — fully functional
- ✅ EPS — fully functional
- ⚠️ PNG — disabled (requires libgd, not available)
- ⚠️ ISMAP — disabled (requires PNG/libgd)

## Patches

1. `0001-src-main.c.patch` — TMPDIR compliance (R10/E002)
   - mscgen hardcoded `/tmp` for `mkstemp()` calls
   - Patched to use `$TMPDIR` environment variable
   - Required for OpenHarmony sandboxed storage policy

## Dependencies

- flex (lexer generation)
- bison (parser generation)

## Installation

```bash
tar xf mscgen-0.20-ohos-aarch64.tar.gz
# Binary installed to $PREFIX/bin/mscgen
```

## Usage Example

```bash
mscgen -T svg -i input.msc -o output.svg
mscgen -T eps -i input.msc -o output.eps
```
