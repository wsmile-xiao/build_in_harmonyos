# sfarklib

sfArkLib is a C++ library for decoding sfArk-compressed SoundFont files.

## HarmonyOS PC adaptation

| Version | Status | Build system | Dependency |
| --- | --- | --- | --- |
| 2.24 | built | Makefile/custom Conan recipe | zlib/1.3.1 |

The HarmonyOS package provides `sfArkLib.h` and the static library
`libsfark.a`. Consumers must implement the four callbacks declared by the
public header.

## Upstream

- Repository: https://github.com/raboof/sfArkLib
- License: GPL-3.0-or-later
