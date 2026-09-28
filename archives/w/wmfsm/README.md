# wmfsm

`wmfsm` is a Window Maker dockapp that displays mounted filesystem usage.
Version 0.36 is packaged for HarmonyOS PC arm64 as the Conan application
`wmfsm/0.36`.

## Features

- Shows usage information for mounted filesystems.
- Provides configurable appearance and dockapp window behavior through X11.

## HarmonyOS adaptation

HarmonyOS PC exposes mounted filesystems through `/proc/mounts` and does not
provide a readable `/etc/mtab`. This package keeps the upstream `/etc/mtab`
path when available and falls back to `/proc/mounts` when it cannot be opened.

The package depends on the published `libdockapp/0.7.3`, `libx11/6.4.0`,
`libxext/6.4.0`, and `libxpm/3.5.17` Conan packages. It provides the `wmfsm`
command; it does not export a C/C++ library.

## Run

```sh
wmfsm --version
wmfsm --help
wmfsm
```

The normal dockapp run needs an X server and a dock-capable window manager.
`--version` and `--help` can be used without a display. The mount-table fallback
is covered by the HarmonyOS consumer test in `0.36/test_package/`.

## References

- [Upstream wmfsm project](https://www.dockapps.net/wmfsm)
- [Official wmfsm 0.36 source archive](https://www.dockapps.net/download/wmfsm-0.36.tar.gz)
