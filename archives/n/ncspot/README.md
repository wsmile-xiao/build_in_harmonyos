# ncspot

Cross-platform ncurses Spotify client written in Rust, inspired by ncmpc and the likes.

## Description

ncspot is a terminal-based Spotify client that provides a visual interface for browsing and controlling Spotify playback. It uses the librespot library for Spotify protocol communication and the Cursive crate for the terminal UI.

## Available Versions

- 1.1.2 (published, 2026-06-17)

## Build Configuration (OHOS)

On OpenHarmony, ncspot is built with:
- **Audio backend**: portaudio_backend (instead of default pulseaudio_backend)
- **TUI backend**: crossterm_backend (pure Rust, no ncurses linking)
- **Build system**: Cargo (Rust)
- **Rust version**: 1.95.0+

## Dependencies

- portaudio (for audio output)
- openssl (for TLS/HTTPS)
- Rust toolchain 1.79.0+

## Source

https://github.com/hrkfdn/ncspot
