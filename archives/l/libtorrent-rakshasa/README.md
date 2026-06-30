# libTorrent (rakshasa)

libTorrent is a BitTorrent library written in C++ for \*nix, with a focus on high performance and good code. The library differentiates itself from other implementations by transferring directly from file pages to the network stack.

## Version

- **0.16.12** (2026-05-18)

## Dependencies

- libcurl >= 8.19.0
- zlib >= 1.3.1
- OpenSSL >= 3.5.6
- pthread

## Build System

- **Autotools** (autoconf/automake/libtool)
- Requires autoreconf -ivf to generate configure script

## Known Issues

- configure.ac uses PKG_CHECK_MODULES which requires pkg.m4
- Copy pkg.m4 from pkg-config installation to scripts/ directory before running autoreconf

## Related Projects

- [rtorrent](https://github.com/rakshasa/rtorrent) - high performance ncurses based torrent client

## License

GPL-2.0-or-later

## Source

https://github.com/rakshasa/libtorrent