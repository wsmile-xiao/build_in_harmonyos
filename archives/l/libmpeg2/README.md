# libmpeg2

A library for decoding MPEG-2 and MPEG-1 video streams.

## Description

libmpeg2 is a free library for decoding MPEG-2 and MPEG-1 video streams. It is used by applications such as mpeg2dec for video playback and processing.

## Compiled Version

- Version: 0.5.1
- Build System: autotools
- Build Date: 2026-05-29

## Installation

Use cmd-pkgs public installation script:

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libmpeg2 0.5.1
```

## Usage

After installation, the library provides:

- **mpeg2dec**: MPEG video decoder executable
- **libmpeg2**: Shared library for MPEG decoding

Verify installation:

```bash
mpeg2dec --version
pkg-config --cflags --libs libmpeg2
```

Example output:

```
-I/storage/Users/currentUser/usr/local/include -L/storage/Users/currentUser/usr/local/lib -lmpeg2
```

## Dependencies

None (standalone library)

## License

GPL-2.0-or-later

## Source

https://libmpeg2.sourceforge.net/