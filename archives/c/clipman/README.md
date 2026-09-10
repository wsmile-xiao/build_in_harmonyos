# Clipman

A simple clipboard manager for Wayland, with support for persisting copy buffers after an application exits.

- Website: https://github.com/chmouel/clipman
- Source: https://github.com/chmouel/clipman
- License: GPL-3.0-only
- Build system: Go
- Category: Wayland utility

## Description

Clipman records clipboard events (typically run as `wl-paste --watch clipman store`),
keeps a JSON history file, and lets the user pick entries back (`clipman pick`)
or wipe them (`clipman clear`). This snapshot is the upstream commit behind the
Debian/Ubuntu `1.2.0+git20200218.39fd4fe` package.
