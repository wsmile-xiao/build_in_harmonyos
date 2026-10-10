# xeus - C++ Jupyter Kernel Protocol Library

## Description

xeus is a C++ library that facilitates the implementation of kernels for Jupyter.
It takes the burden of implementing the Jupyter Kernel protocol so developers
can focus on implementing the interpreter part of their kernels.

## Version

- Latest compiled version: 6.0.5

## Build Information

- Build system: CMake (3.16+)
- Compiler: Clang 15.0.4
- Platform: OpenHarmony (aarch64)
- Library type: Static only (shared disabled for OHOS compatibility)

## Dependencies

- nlohmann_json/3.12.0 (header-only JSON)
- libuuid/2.42.2 (UUID generation on Unix/OHOS)

## Usage

xeus is a library package. Consumers link against `libxeus.a` and include
`<xeus/*.h>` headers. The standard pattern is to inherit from
`xeus::xinterpreter` and implement the virtual methods.

## License

BSD-3-Clause
