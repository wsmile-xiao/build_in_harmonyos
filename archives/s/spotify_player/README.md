# spotify_player

Terminal Spotify client written in Rust with an interactive UI.

## Features
- Full Spotify playback control
- Interactive terminal UI
- Playlist management
- Search functionality

## OpenHarmony Adaptation

This is a pre-compiled binary approach using gcompat for glibc compatibility.

### Method: gcompat (glibc → musl shim)
- Downloaded aarch64-linux-gnu (glibc) binary from GitHub releases
- Applied patchelf to replace glibc dependencies:
  - libc.so.6, libm.so.6, libpthread.so.0, libdl.so.2 → libgcompat.so.0
  - ld-linux-aarch64.so.1 → libglibc-shim.so
  - Set interpreter to /lib/ld-musl-aarch64.so.1
  - Set RPATH to ~/usr/local/lib

### Dependencies
- libgcompat.so.0 (pre-installed)
- libglibc-shim.so (pre-installed)
- libasound.so.2 (ALSA, from Alpine, bundled)
- libdbus-1.so.3 (pre-installed)
- libssl.so.1.0.0, libcrypto.so.1.0.0 (pre-installed)
- libgcc_s.so.1 (musl version from Alpine)

### Version Note
v0.23.0 does not have aarch64-linux-gnu binary in GitHub releases. Using v0.22.1 (latest with aarch64-gnu support).
