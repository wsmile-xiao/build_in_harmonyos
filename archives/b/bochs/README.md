# Bochs

Bochs is a portable x86 and x86-64 system emulator.

- Upstream: https://github.com/bochs-emu/Bochs
- License: LGPL-2.1-or-later
- Package type: command-line tool

## HarmonyOS PC adaptation

The HarmonyOS package provides the headless `nogui` emulator, `bximage`,
BIOS/VGA firmware and keymaps. SDL, terminal UI, readline and loadable plugins
are disabled because their target packages are not available in the competition
artifact repository. The functional test executes guest BIOS code and verifies
the no-boot-device panic.

See each version's `notes.md` for build and verification details.

## Versions

- `3.0` - initial HarmonyOS PC adaptation (`built`)
