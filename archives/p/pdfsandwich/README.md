# pdfsandwich

pdfsandwich is a command-line tool for generating "sandwich" OCR PDF files.
It takes a PDF file with images (e.g., scanned documents) and adds a text
layer containing the OCR results, making the PDF searchable.

## Features

- OCR processing using Tesseract
- Image preprocessing using ImageMagick and optionally unpaper
- Multi-threaded processing for faster OCR
- Supports multiple languages via Tesseract
- Various layout options (single/double page)

## Dependencies

- Runtime: tesseract, imagemagick (convert), optionally unpaper, ghostscript, hocr2pdf
- Build: OCaml compiler (>= 4.13), GNU make, gawk

## Version 0.1.7

- Build system: autotools-like (simple configure script)
- Language: OCaml
- Binary: single executable (pdfsandwich)
