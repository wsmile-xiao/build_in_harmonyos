# msgpack-cxx

MessagePack is an efficient binary serialization format for C++. It lets you exchange data among multiple languages like JSON but is faster and smaller.

## Overview

- **License**: BSL-1.0 (Boost Software License)
- **Build System**: CMake (header-only INTERFACE library)
- **Dependencies**: Boost (optional, disabled in this adaptation)

## Adaptation Notes

- Header-only library, no binary output
- Boost dependency disabled via `MSGPACK_USE_BOOST=OFF`
- Documentation build disabled via `MSGPACK_BUILD_DOCS=OFF`
