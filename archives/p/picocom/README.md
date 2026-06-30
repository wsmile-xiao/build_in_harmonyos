# picocom

Minimal dumb-terminal emulation program for serial port communication.

picocom is a minimal dumb-terminal emulation program that allows
communication with serial port devices. It is designed to be simple,
lightweight, and easy to use, making it ideal for embedded systems
development and debugging.

## Features

- Serial port terminal emulation
- Custom baudrate support
- Line editing with linenoise library
- UUCP-style and flock locking
- File upload/download capabilities
- Escape character control

## Compiled-in Options (2024.07)

- TTY_Q_SZ: 0 (unlimited output queue)
- HIGH_BAUD: enabled
- USE_FLOCK: enabled
- LINENOISE: enabled (command history support)

## Versions

| Version | Status | Date |
|---------|--------|------|
| 2024.07 | published | 2026-05-25 |