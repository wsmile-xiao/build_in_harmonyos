# chafa

Chafa is a library and command-line utility for converting images to ANSI/Unicode character art.

## Description

Chafa is a powerful image-to-text conversion tool that can render images using terminal graphics protocols like Sixel or ANSI art. It supports various input formats through optional image decoding libraries.

## Features

- Converts images to ANSI/Unicode character art
- Supports multiple output formats (ANSI, Sixel, etc.)
- High-quality color approximation
- Efficient processing with SIMD optimizations (where available)

## Version History

| Version | Status | Date |
|---------|--------|------|
| 1.18.2 | published | 2026-05-25 |

## OpenHarmony Adaptation Notes

- Platform: aarch64-unknown-linux-ohos
- Build system: autotools
- Key modifications: config.guess/config.sub patched for HarmonyOS support
- Tools disabled (--without-tools) due to freetype2 dependency

## Links

- Homepage: https://hpjansson.org/chafa/
- GitHub: https://github.com/hpjansson/chafa