# libmpdclient

A stable, documented, asynchronous API library for interfacing MPD in the C, C++ & Objective C languages.

## Description

libmpdclient is a library for C, C++ and Objective C applications that want to communicate with a Music Player Daemon (MPD) server. It provides a stable, documented, asynchronous API.

## Compiled Version

- Version: 2.23
- Build System: meson
- Build Date: 2026-05-29

## Installation

Use the cmd-pkgs public installation script:

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libmpdclient 2.23
```

## Usage

After installation, use pkg-config to link against the library:

```bash
pkg-config --cflags --libs libmpdclient
```

Example output:
```
-I/storage/Users/currentUser/usr/local/include -L/storage/Users/currentUser/usr/local/lib -lmpdclient
```

## Dependencies

None (standalone library)

## License

BSD-2-Clause and BSD-3-Clause

## Source

https://www.musicpd.org/libs/libmpdclient/