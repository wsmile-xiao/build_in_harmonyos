# xfce4-pulseaudio-plugin 0.5.1 — OpenHarmony aarch64

Pulseaudio panel plugin for the Xfce desktop environment, compiled for OpenHarmony (aarch64).

## Build Details

- **Platform**: aarch64-unknown-linux-ohos
- **Compiler**: clang 15.0.4
- **Build System**: autotools

## Key Adaptations

1. XDT autoconf macros replaced with standard PKG_CHECK_MODULES
2. Autoconf-generated auxiliary files included as patches (upstream tarball lacks pre-generated configure)
3. Optional features disabled: keybinder, libnotify, libcanberra, libxfce4windowing
4. HAVE_GNUC_VISIBILITY disabled in config.h

## Patches

33 patches applied — see manifest.yaml for full list.

## Installation

```bash
tar xf xfce4-pulseaudio-plugin-0.5.1-ohos-aarch64.tar.gz
cp -r usr/local/lib/xfce4/panel/plugins/libpulseaudio-plugin.so /usr/local/lib/xfce4/panel/plugins/
cp -r usr/local/share/xfce4/panel/plugins/pulseaudio.desktop /usr/local/share/xfce4/panel/plugins/
```
