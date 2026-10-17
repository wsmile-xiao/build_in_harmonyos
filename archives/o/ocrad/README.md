# ocrad

GNU Ocrad — Optical Character Recognition program and library.

ocrad is an OCR (Optical Character Recognition) program based on a feature
extraction method. It reads images in png or pnm formats and produces text
in byte (8-bit) or UTF-8 formats.

## Build Artifacts

- `bin/ocrad` — OCR command-line tool
- `lib/libocrad.a` — static library for OCR functionality
- `include/ocradlib.h` — C API header

## Dependencies

- libpng/1.6.58.2 (PNG image I/O)
