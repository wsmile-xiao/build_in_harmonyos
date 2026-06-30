# libimagequant

**Description**: Palette quantization library that powers pngquant and other PNG optimizers.

**License**: GPL v3 or later (FLOSS), commercial license available for non-GPL use.

## About

Libimagequant is a small, portable C library for high-quality conversion of RGBA images to 8-bit indexed-color (palette) images. It's ideal for generating tiny PNG images and nice-looking GIFs.

## Key Features

- High-quality palette quantization
- Converts RGBA images to 8-bit indexed-color
- Supports alpha channel in palette
- No external dependencies
- C99 compatible

## Available Versions

- **2.18.0** (published): 2026-05-22

## Usage

Include the header file:
```c
#include <libimagequant.h>
```

Link with the library:
```bash
gcc yourprogram.c -limagequant -lm
```

Or link statically:
```bash
gcc yourprogram.c /path/to/libimagequant.a -lm
```

## Dependencies

None (standalone library).

## Related Tools

- **pngquant**: PNG compression tool using libimagequant

## Links

- GitHub: https://github.com/ImageOptim/libimagequant
- Documentation: https://pngquant.org/lib/