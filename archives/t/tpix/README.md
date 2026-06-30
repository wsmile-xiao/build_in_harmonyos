# tpix

Simple terminal image viewer using the kitty graphics protocol.

## Description
tpix is a terminal image viewer written in Nim. It is compatible with terminal emulators that support the kitty graphics protocol and uses the Pixie graphics library to read and render images.

## Supported Formats
PNG, JPG, GIF (not animated), BMP, QOI, PPM, SVG (limited)

## Build Information
- Language: Nim
- Build system: NimScript/nimble (custom)
- Dependencies: Nim >= 1.4.8, pixie, cligen
- Versions: 1.0.3

## Usage
```bash
tpix image.jpg
cat image.jpg | tpix
```
