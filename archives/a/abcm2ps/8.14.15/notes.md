# abcm2ps 8.14.15 OpenHarmony adaptation

## Source

The package version is `8.14.15` as requested. It packages upstream release
`v8.14.15` from the abcm2ps GitHub repository.

## Build and tests

- The bundled `configure` script generates a Makefile and `config.h`.
- `make -j1` builds the converter.
- `make test` converts the bundled ABC examples to PostScript.
- The test package converts a small ABC input and asserts that the output file
  is non-empty.

## Dependencies

No Conan dependencies are declared. Optional Pango detection is left disabled
when the target environment has no matching `pkg-config` modules.
