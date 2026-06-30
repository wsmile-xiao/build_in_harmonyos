# Peek

Peek is an animated GIF screen recorder for Linux. It creates silent GIF recordings of your desktop screen, making it easy to share quick screenshots with animations.

## Features
- Record screen area as animated GIF
- Support for FFmpeg recording backend
- Desktop integration with GNOME Shell
- Configurable recording settings

## Dependencies
- GTK3 (gtk+-3.0 >= 3.20) — **CRITICAL**: Not available on OpenHarmony
- glib-2.0 >= 2.38
- cairo
- pango
- keybinder-3.0 (optional)

## OpenHarmony Status
**Status**: ❌ Build failed — GTK3 dependency unavailable

GTK3 (gtk+-3.0) is not available on OpenHarmony as a precompiled package or development files. This blocks compilation of peek and all other GTK3-dependent GNOME applications.

## Website
https://github.com/phw/peek