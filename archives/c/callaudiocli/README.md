# callaudiocli

CLI tool and shared library for audio call mode management, from the [callaudiod](https://gitlab.com/mobian1/callaudiod) project.

## Components

- **callaudiocli**: Command-line tool for selecting audio modes, enabling speaker, and muting microphone
- **libcallaudio-0.1**: Shared library providing the CallAudio DBus client API

## Build

```bash
meson setup builddir --prefix=<prefix> --buildtype=debugoptimized -Dgtk_doc=false
ninja -C builddir
meson install -C builddir --destdir=<staging>
```

## Dependencies

- glib (gobject-2.0, gio-unix-2.0)

## Notes

- The callaudiod daemon (src/) is conditionally built when PulseAudio and ALSA are available
- On HarmonyOS, only the CLI tool and library are built
