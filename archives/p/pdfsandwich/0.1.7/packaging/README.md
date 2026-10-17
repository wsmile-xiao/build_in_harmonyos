# Packaging

This directory contains packaging artifacts for pdfsandwich 0.1.7.

## Build Artifacts

- Binary: `bin/pdfsandwich` (OCaml native executable)
- Man page: `share/man/man1/pdfsandwich.1.gz`
- Documentation: `share/doc/pdfsandwich/`

## Package Type

- `application` (command-line tool, not a library)

## Dependencies

- Build-time: `ocaml/4.14.1.1.4` (tool_requires)
- Runtime: tesseract, imagemagick, ghostscript (external system tools, not conan)
