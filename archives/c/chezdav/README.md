# chezdav

chezdav is a small command-line WebDAV server from the GNOME phodav project. It shares a local directory over HTTP/WebDAV and supports local-only binding, read-only mode, and digest authentication.

## Features

- Share an arbitrary local directory through WebDAV.
- Bind to loopback only or to all network interfaces.
- Serve content read-only when requested.
- Protect the exported tree with an htdigest file.

## HarmonyOS adaptation

- Builds the upstream phodav 3.0 source with Meson on HarmonyOS PC/aarch64.
- Disables optional Avahi/mDNS support because it is not required for the core WebDAV server.
- Links the bundled phodav library statically into `chezdav`; the unrelated `spice-webdavd` target is not built and the package exports only the command-line tool.
- Uses a private RFC 4122 UUID helper because the published shared libsoup3 artifact does not export `g_uuid_string_random`, while the old bundled compatibility source conflicts with GLib 2.88 UUID macros.
- Keeps the upstream 18-case localhost WebDAV test suite enabled and adds an end-to-end packaged-binary test.

## Dependencies

- glib2/2.88.0
- libsoup3/3.6.5-r2
- libxml2/2.15.3.1
- zlib/1.3.1.1 (dependency graph override required by libsoup3)

## References

- https://gitlab.gnome.org/GNOME/phodav
- https://download.gnome.org/sources/phodav/3.0/
