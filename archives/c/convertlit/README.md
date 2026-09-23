# ConvertLIT

ConvertLIT 1.8 provides the `clit` command-line program for inspecting and
expanding Microsoft Reader `.lit` eBooks or rewriting them to DRM1 format.

## HarmonyOS adaptation

- Builds the two upstream plain Makefiles with the Conan-selected C compiler.
- Replaces the bundled libtommath 0.30 path with the published
  `libtommath/1.3.0` package staged in a build-private prefix.
- Adds the standard C headers and LZX declarations required by Clang 15/C99.
- Packages the `clit` executable and runs it against both its usage path and a
  deliberately malformed LIT input.

The upstream 1.8 archive contains no automated test suite or test target.

## References

- http://www.convertlit.com/
- https://formulae.brew.sh/formula/convertlit
- https://ports.macports.org/port/convertlit/details/
