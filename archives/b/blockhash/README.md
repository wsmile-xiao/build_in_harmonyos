# blockhash

Perceptual image hash calculation tool for HarmonyOS.

## Overview

blockhash is a tool for calculating perceptual image hashes based on the algorithm described in "Block Mean Value Based Image Perceptual Hashing" by Bian Yang, Fan Gu and Xiamu Niu.

This is a HarmonyOS-adapted version that uses stb_image instead of MagickWand (ImageMagick) for image loading.

## Version

- **Original**: 0.3.2 (wscript VERSION)
- **HarmonyOS**: 0.3.2-harmonyos

## Features

- Calculate perceptual hash for images (JPEG, PNG, BMP, GIF, PSD, TGA, etc.)
- Two hashing methods: quick (rounded blocks) and precise (weighted pixels)
- Configurable hash bits (default: 16, output: 64-character hex)
- No external dependencies (stb_image embedded)

## Installation

### From Precompiled Package

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- blockhash 0.1
```

### Manual Build

```bash
# Download source
curl -fsSL https://download.savannah.nongnu.org/releases/blockhash/blockhash-0.1.tar.gz -o blockhash-0.1.tar.gz
tar xzf blockhash-0.1.tar.gz
cd blockhash-0.1

# Apply stb_image patch (if using original source)
curl -fsSL https://raw.githubusercontent.com/nothings/stb/master/stb_image.h -o stb_image.h
# Replace MagickWand with stb_image (see patches/0001-use-stb-image.patch)

# Build
clang -O3 -DVERSION="0.3.2-harmonyos" -o blockhash blockhash.c -lm

# Sign ELF (HarmonyOS requirement)
/data/service/hnp/bin/binary-sign-tool sign -inFile blockhash -outFile blockhash.signed -selfSign 1
mv blockhash.signed blockhash
chmod 755 blockhash

# Install
cp blockhash ~/usr/local/bin/
```

## Usage

```bash
# Basic usage
blockhash image.jpg

# Quick method (faster, less accurate)
blockhash --quick image.jpg

# Custom bits (must be multiple of 4)
blockhash --bits 8 image.jpg   # 16-character hash
blockhash --bits 16 image.jpg  # 64-character hash (default)
blockhash --bits 32 image.jpg  # 256-character hash

# Debug mode (print 2D hash map)
blockhash --debug image.jpg

# Multiple files
blockhash *.jpg *.png

# Show version
blockhash --version
```

## Example Output

```
$ blockhash testdata/00002701.jpg
f81bf99ffb803400e07f8c7d049f058706013e233fe33fe11f600e638ea30def  testdata/00002701.jpg
```

## HarmonyOS Adaptation

### Changes from Original

| Component | Original | HarmonyOS Version |
|-----------|---------|-------------------|
| Image Library | MagickWand (ImageMagick) | stb_image.h |
| Dependencies | ImageMagick + deps | None |
| Build System | waf | Manual clang |
| Version | 0.3.2 | 0.3.2-harmonyos |

### Why stb_image?

- **E064 Issue**: ImageMagick's autotools configure fails on HMDFS (HarmonyOS distributed filesystem) due to temporary directory permission issues
- **Dependency Chain**: ImageMagick requires 50+ dependencies (libjpeg, libpng, libtiff, zlib, etc.)
- **No Precompiled Package**: ImageMagick not available in cmd-pkgs

stb_image solves these problems:
- Single header file, no compilation needed
- No external dependencies
- Supports common image formats (JPEG, PNG, BMP, GIF)
- Easy to embed in source code

## Supported Formats

- JPEG
- PNG
- BMP
- GIF
- PSD
- TGA
- PIC
- PNM

## Limitations

Compared to original MagickWand version:
- Fewer image formats (no TIFF, WebP, HEIC, etc.)
- No color profile handling
- No image transformations

For most perceptual hashing use cases, these limitations are acceptable.

## Technical Details

### Algorithm

The algorithm divides the image into N×N blocks and compares each block's mean value to the median of blocks in the same horizontal band. The hash output is a 2D bit map where 1 indicates a block is brighter than the median.

### Hash Comparison

Two images with similar content will have similar hashes. The Hamming distance between hashes indicates similarity:
- Distance 0: Identical images
- Distance < 10: Very similar
- Distance > 20: Different images

## License

MIT License (same as original)

## References

- [Original Repository](https://github.com/commonsmachinery/blockhash)
- [stb_image](https://github.com/nothings/stb)
- [Block Mean Value Based Image Perceptual Hashing Paper](https://www.researchgate.net/publication/224197125_Block_Mean_Value_Based_Image_Perceptual_Hashing)

---

**Archived by**: OpenHarmony Compile Agent  
**Archive Date**: 2026-05-07  
**Archive Location**: `archives/b/blockhash/0.1/`