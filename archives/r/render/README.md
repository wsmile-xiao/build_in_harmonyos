# render (libXrender)

X Rendering Extension client library for X11.

## Description

libXrender provides the client-side API for the Render extension to the X11 protocol.
This extension allows for alpha blending, gradient fills, and image transformations
within the X Window System.

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 0.9.12 | built | 2026-05-26 |

## Build Notes

See [0.9.12/notes.md](0.9.12/notes.md) for detailed build information.

## Dependencies

- xorgproto (renderproto >= 0.11)
- libX11

## Patches

- 0001-config.guess.patch: HarmonyOS/OpenHarmony platform detection
- 0002-config.sub.patch: HarmonyOS/OpenHarmony subsystem recognition

## License

MIT License - see the COPYING file in the source distribution.
