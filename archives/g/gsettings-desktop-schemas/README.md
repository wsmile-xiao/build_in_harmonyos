# gsettings-desktop-schemas

Collection of GSettings schemas for the GNOME desktop, including helper
header files with enum definitions.

## Versions

- 49.1 - built (2026-08-06)

## Description

This package provides:
- `gdesktop-enums.h`: C header with desktop enum types
- GSettings schema XML files (32 schemas)
- pkg-config file for consumer integration
- Internationalization translations (48 languages)

## Dependencies

- meson (build)
- ninja (build)
- glib-mkenums (build, requires perl)
- pkg-config (build/runtime)
