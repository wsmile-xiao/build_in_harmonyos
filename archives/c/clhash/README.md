# clhash

`clhash` is a C library implementing fast 64-bit universal hashing via
carry-less multiplication, with a C++ wrapper.

- Version: 1.0.0
- Upstream: https://github.com/simdhash/clhash
- Build system: CMake
- Conan package: `clhash/1.0.0@ohpcd/stable`
- License: Apache-2.0

The recipe builds the upstream CTest targets, packages the static library and
public header, and provides the upstream CMake package configuration for
downstream consumers.
