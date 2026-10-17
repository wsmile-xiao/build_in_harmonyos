# ympd

ympd is a lightweight web interface that lets a browser control a Music Player Daemon (MPD) server.

## Features

- Controls playback, playlists, queue, outputs, and library browsing through MPD.
- Serves a browser interface over HTTP and uses WebSockets for live control.
- Supports IPv6 and serves the web assets embedded in the executable.

## HarmonyOS PC

The package builds natively for HarmonyOS PC on AArch64 with Clang and CMake. Its web assets are embedded in the executable, and libmpdclient and OpenSSL are resolved through Conan. The service listens on port 8080 by default and connects to MPD at `127.0.0.1:6600` unless configured otherwise.

## Dependencies

- Build: `libmpdclient/2.23`, `openssl/3.5.8.1`
- Runtime: the shared `libmpdclient/2.23` library and a reachable MPD server
- Run the executable with the Conan runtime environment active so the shared library can be found.

## References

- Upstream: https://github.com/notandy/ympd
- Release: https://github.com/notandy/ympd/releases/tag/v1.3.0
