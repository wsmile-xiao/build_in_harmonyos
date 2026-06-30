# cpufetch

CPU architecture fetching tool for Linux/Android/HarmonyOS.

Displays detailed CPU information (model, cores, frequencies, cache, etc.) with an ASCII art logo.

- **License**: GPL-2.0-only
- **Homepage**: https://github.com/Dr-Noob/cpufetch
- **Version**: 1.07

## OpenHarmony Build Notes

- Built with clang (CC=clang, CFLAGS="-O2 -fPIC")
- Custom Makefile build system (no configure script)
- No external dependencies
- Platform detection modified for HarmonyOS/ohos on aarch64