# libkscreen

KDE Plasma screen management library.

## Description
Provides the KScreen namespace (KF6Screen / KF6ScreenDpms shared libraries,
the kscreen-doctor CLI and the kscreen_backend_launcher D-Bus service) for
querying and manipulating display configurations, with pluggable backends
(Wayland via plasma-wayland-protocols, fake JSON; XRandR is X11-only and is
not built on OHOS).

## Homepage
https://invent.kde.org/plasma/libkscreen

## License
LGPL-2.1-or-later AND BSD-3-Clause AND GPL-2.0-or-later

## Build System
CMake (KDE ECM)

## Dependencies
- qtbase/6.11.1.2
- qtwayland/6.11.1
- wayland/1.22.0 (+ wayland/1.22.0 build tool package for wayland-scanner)
- ecm/6.26.0
- plasma-wayland-protocols 1.21.0 (carried in-recipe; not a conan package)

## Versions
- 6.7.2: initial HarmonyOS PC adaptation (2026-09-19)
