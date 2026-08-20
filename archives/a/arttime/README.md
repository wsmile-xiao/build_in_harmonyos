# arttime

CLI application that blends beauty of ASCII/text art with functionality of clock/timer/pattern-based time manager in terminal.

## Overview

- **Homepage**: https://github.com/poetaman/arttime
- **License**: Custom (LICENSE_CODE, LICENSE_ART, LICENSE_ADDENDUM_CFLA)
- **Language**: Shell (zsh)
- **Build system**: install.sh (zsh script — NOT CMake/Autotools/Makefile)

## Description

arttime is an application that runs in your terminal emulator. It blends the beauty of text art with the functionality of a feature-rich clock/timer/pattern-based time manager.

## Build Artifacts

- `bin/arttime` — main CLI script (zsh)
- `bin/artprint` — companion script for printing art
- `share/arttime/textart/` — 516+ ASCII/ANSI art files
- `share/arttime/keypoems/` — 22 keypoem files
- `share/arttime/src/arttime.zsh` — main source file
- `share/arttime/doc/` — documentation
- `share/man/man1/` — man pages

## System Dependencies

- zsh >= 5.7 (available on OHOS as zsh 5.9, aarch64-unknown-linux-musl)
- Optional: fzf, PulseAudio/PipeWire, vorbis-tools

## OHOS Adaptation Notes

- Pure shell script — no compilation needed
- OHOS zsh 5.9 is available but missing standard autoload functions (is-at-least, compinit)
- The Conan recipe uses conan.tools.files.copy() to package files directly, bypassing install.sh
- test_package creates the missing is-at-least function before running arttime --version
- Platform detection in install.sh: HarmonyOS reports as "Linux" via uname -a (correct behavior)

## Versions

| Version | Status | Date |
|---------|--------|------|
| 2.5.0 | built | 2026-08-18 |
