# pulseaudio

PulseAudio is a sound system for POSIX OSes, providing a proxy between applications and audio devices.

## Description

PulseAudio provides a daemon (pulseaudio) and a client library (libpulse) for audio playback and recording. This archive provides the **client library only** (libpulse, libpulse-simple, libpulse-mainloop-glib) for OpenHarmony, enabling applications to connect to a PulseAudio server for audio operations.

## Features

- Client library for audio playback and recording (libpulse)
- Simple API wrapper (libpulse-simple)
- GLib mainloop integration (libpulse-mainloop-glib)
- Stream management and volume control
- Sample cache and playback operations

## Version History

| Version | Status | Date |
|---------|--------|------|
| 17.0 | built | 2026-05-25 |

## OpenHarmony Adaptation Notes

- Platform: aarch64-unknown-linux-ohos
- Build system: meson
- Only client libraries built (daemon disabled)
- NLS (localization) disabled to avoid glib libintl.h proxy conflict
- Required dependency: libsndfile 1.2.2

## Links

- Homepage: https://www.freedesktop.org/wiki/Software/PulseAudio/
- Source: https://gitlab.freedesktop.org/pulseaudio/pulseaudio/