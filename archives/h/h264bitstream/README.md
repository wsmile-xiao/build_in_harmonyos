# h264bitstream

H.264 bitstream parsing library and analysis tool.

## Description

h264bitstream is a C library for reading and writing H.264 video bitstreams in Annex B format. It provides a complete set of functions for parsing NAL units, SPS, PPS, slice headers, SEI messages, and AVC configuration boxes.

The library includes `h264_analyze`, a command-line tool for analyzing H.264 bitstreams.

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 0.2.0 | published | 2026-06-17 |

## Build System

autotools (requires `autoreconf -fi` to generate configure script)

## Dependencies

No external dependencies beyond standard C library.

## Installed Files

- `bin/h264_analyze` — H.264 bitstream analysis tool
- `lib/libh264bitstream.so` — Shared library
- `lib/libh264bitstream.a` — Static library
- `include/h264bitstream/*.h` — Header files
- `lib/pkgconfig/libh264bitstream.pc` — pkg-config file
