# kbd-bkeymaps

`kbd-bkeymaps` contains binary keyboard maps generated from the Linux Kbd project's distributed keymap sources for use with BusyBox `loadkmap`.

## Features

- Includes the Kbd 2.8.0 i386 keymap set in BusyBox-compatible `bkeymap` format.
- Installs compressed maps under `share/bkeymaps/<layout>/<name>.bmap.gz`.
- Contains data only; it does not install `loadkeys` or another executable.

## HarmonyOS adaptation

The `loadkeys` converter is built and run natively on HarmonyOS AArch64 during packaging. It is used only to generate the maps and is not included in the installed package. The compressed map files are runtime data and do not depend on Conan libraries.

## Dependencies

- Build tools: Flex 2.6.4 and Bison 3.8.2.
- Runtime dependencies: none.

## References

- [Kbd project](https://kbd-project.org/)
- [Kbd 2.8.0 source archive](https://www.kernel.org/pub/linux/utils/kbd/kbd-2.8.0.tar.xz)
- [BusyBox `loadkmap` format reader](https://sources.debian.org/src/busybox/1%3A1.37.0-6/console-tools/loadkmap.c)
