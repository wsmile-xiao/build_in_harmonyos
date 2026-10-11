# rokuecp

`rokuecp` is a C library for discovering and controlling Roku devices through
the External Control Protocol (ECP).

## Features

- Discovers Roku devices with SSDP.
- Queries device, application and live-TV metadata.
- Sends remote-control keys, text, searches and application launch requests.
- Exposes a small C11 API in `rokuecp.h`.

## HarmonyOS PC adaptation

Version 0.2.0 is built as a shared library with the HarmonyOS PC Clang toolchain.
The upstream CMake dependency lookup is mapped to the Conan-provided GSSDP,
libsoup 3 and libxml2 targets; no platform-specific source behavior is changed.

## Dependencies

- gssdp/1.6.6
- libsoup3/3.6.5-r1
- libxml2/2.15.3.1
- glib2/2.88.0（公共头依赖）

## References

- Homepage: https://github.com/benthetechguy/rokuecp
- Source: https://github.com/benthetechguy/rokuecp
