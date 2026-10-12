# SPLAT!

SPLAT! is an RF signal propagation, loss, and terrain analysis suite for the 20 MHz to 20 GHz spectrum.

## OHOS adaptation

- Builds the upstream C and C++ sources directly with Conan profile compilers.
- Uses published `bzip2/1.0.8` and `zlib/1.3.1` dependencies.
- Packages SPLAT! plus its city, terrain conversion, font, and bearing utilities.
- Preserves upstream source behavior without patches.
- Tests installed command behavior and the OHOS writable temporary-directory path.

## References

- https://www.qsl.net/kd2bd/splat.html
