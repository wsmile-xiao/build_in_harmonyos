# wiiuse

**Feature-complete cross-platform Wii Remote access library**

wiiuse is a C library for communicating with Nintendo Wii Remote (Wiimote) controllers via Bluetooth.

## OHOS Build Notes

On OHOS, the Bluetooth stack (Bluez) is not available, so wiiuse is built as a **stub library**:

- The library compiles and links correctly
- API functions like `wiiuse_init()`, `wiiuse_version()` work
- Bluetooth I/O functions (`wiiuse_os_find`, `wiiuse_os_connect`, etc.) return 0 — no hardware connectivity
- This enables downstream projects to link against wiiuse without modifying their code

## Available Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 0.15.7 | built | 2026-06-02 | OHOS stub build (no Bluetooth) |