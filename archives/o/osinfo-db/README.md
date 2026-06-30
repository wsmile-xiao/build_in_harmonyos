# osinfo-db

## What is it?

osinfo-db is a database of operating system, platform, and device information used by the libosinfo library. It contains XML/JSON data files describing various OS distributions, hardware platforms, and install scripts.

## Key Features

- Pure data package — no compilation required
- Contains 1070+ data files covering OS metadata, device IDs, and install scripts
- Used by libosinfo for OS detection and VM provisioning

## OHOS/HarmonyOS Adaptation

- **Build type**: script (data-only, no compiler needed)
- **No patches required** — pure data files, no source modifications
- **Installation path**: `$PREFIX/share/osinfo/`

## Version 20250124

- Status: published
- Build date: 2026-06-08
- No compilation issues encountered