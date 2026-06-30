# phodav

## About

phởdav is a WebDav server implementation using libsoup (RFC 4918).

## Description

phodav provides a WebDAV server implementation using libsoup. It was initially developed as a filesharing mechanism for Spice, but it is generic enough to be reused in other projects, in particular in the GNOME desktop.

## Tools

- **chezdav**: Allows to share a particular directory (with optional digest authentication)
- **spice-webdavd**: Spice WebDAV daemon for file sharing

## Dependencies

phodav requires the following libraries:
- gio-unix-2.0 >= 2.44
- libsoup-2.4 >= 2.48.0
- libxml-2.0

Optional dependencies:
- avahi-gobject (for Avahi support)
- avahi-client (for Avahi support)

## Compiled Versions

| Version | Status | Build Date | Build System |
|---------|--------|------------|--------------|
| 2.5 | published | 2026-06-17 | meson |

## Homepage

https://gitlab.gnome.org/GNOME/phodav

## License

LGPLv2.1