# pamixer

pamixer is a command-line mixer for PulseAudio. It can control the volume levels of sinks and sources.

## Dependencies

- libpulse (from pulseaudio)
- cxxopts (C++ command line parser library)

## Build

pamixer uses the Meson build system.

```bash
meson setup build
meson compile -C build
meson install -C build
```

## Usage

```
pamixer [OPTIONS]

  -h, --help              help message
  -v, --version           print version info
      --sink INDEX        choose a different sink than the default
      --source INDEX      choose a different source than the default
      --get-volume        get the current volume
      --set-volume VAL    set the volume
  -i, --increase VAL      increase the volume
  -d, --decrease VAL      decrease the volume
  -t, --toggle-mute       switch between mute and unmute
  -m, --mute              set mute
  -u, --unmute            unset mute
      --list-sinks        list the sinks
      --list-sources      list the sources
```
