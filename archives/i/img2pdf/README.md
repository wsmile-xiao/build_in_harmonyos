# img2pdf

Lossless conversion of raster images to PDF.

## Description

img2pdf is a Python library and command line tool to convert images to PDF without re-encoding the image data. This ensures the output PDF is always lossless and typically smaller than conventional conversion methods.

Key features:
- **Always lossless**: the image embedded in the PDF will always have the exact same color information for every pixel as the input
- **Small**: if possible, the difference in filesize between the input image and the output PDF will only be the overhead of the PDF container itself
- **Fast**: if possible, the input image is just pasted into the PDF document as-is without any CPU hungry re-encoding

## Homepage

https://gitlab.mister-muffin.de/josch/img2pdf

## License

LGPL-3.0-or-later

## Usage

```bash
img2pdf --version
img2pdf img1.png img2.jpg -o out.pdf
```

## Available Versions

- **0.6.3** (built, 2026-05-22)

## Notes

- This version removes the pikepdf dependency due to qpdf library issues
- Basic functionality works, some advanced features may be limited
- Requires Pillow (python-pillow) for image processing

## Installation

Download the precompiled package `img2pdf-0.6.3-ohos-aarch64.tar.gz` and extract it.

```bash
tar -xzf img2pdf-0.6.3-ohos-aarch64.tar.gz -C ~/usr/local/
```