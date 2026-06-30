# open62541

open62541 is an open-source and free implementation of OPC UA (Open Platform Communications Unified Architecture) written in the C programming language. The library is targeting the embedded space with a low memory footprint and provides a full OPC UA stack (client and server).

## Features

- OPC UA Client and Server
- Supports all OPC UA security policies and modes
- PubSub support
- Minimal memory footprint
- C/C++ library (no external dependencies)

## Build

- Build system: CMake
- Compiler: clang/clang++
- Version: 1.5.3

## OHOS Adaptation Notes

Requires 2 patches for HarmonyOS/musl platform:
1. `bits/stdio_lim.h` header guard (glibc-specific header, not available on musl)
2. `linux/net_tstamp.h` / txtime structs guard (header conflict on OHOS)
