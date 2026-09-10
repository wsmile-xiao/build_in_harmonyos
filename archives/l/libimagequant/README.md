# libimagequant

**Description**: Palette quantization library that powers pngquant and other PNG optimizers.

**License**: GPL v3 or later (FLOSS), commercial license available for non-GPL use.

## About

Libimagequant is a small, portable library for high-quality conversion of RGBA images to 8-bit indexed-color (palette) images. It's ideal for generating tiny PNG images and nice-looking GIFs.

> Note: since the 4.x series the upstream implementation has been rewritten in
> Rust (`imagequant` crate) behind a stable C API (`libimagequant.h`, shipped by
> the `imagequant-sys` FFI crate). The Conan package form remains a pure C
> static library — C consumers (pngquant/GIMP) link exactly as before.

## Key Features

- High-quality palette quantization
- Converts RGBA images to 8-bit indexed-color
- Supports alpha channel in palette
- C API unchanged across 2.x/4.x
- 4.x core is Rust with threads (rayon) support

## Available Versions

- **2.18.0** (published): 2026-05-22
- **4.4.1** (built): 2026-09-10 — Rust core + C API, cross-built with
  rust-toolchain/1.97.1 for aarch64-unknown-linux-ohos

## Usage

Include the header file:
```c
#include <libimagequant.h>
```

Link with the library:
```bash
gcc yourprogram.c -limagequant -lpthread -lm -ldl
```

Or link statically:
```bash
gcc yourprogram.c /path/to/libimagequant.a -lpthread -lm -ldl
```

## Dependencies

- 2.x: none (standalone pure C library)
- 4.x: build-time `rust-toolchain/1.97.1` + `openssl/3.5.6.1.1` (cargo
  runtime); no runtime deps beyond libc/pthread

## Related Tools

- **pngquant**: PNG compression tool using libimagequant

## Links

- GitHub: https://github.com/ImageOptim/libimagequant
- Documentation: https://pngquant.org/lib/