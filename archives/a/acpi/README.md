# acpi — ACPI Client Utility

acpi is a command-line tool that shows information from the /proc and /sys
filesystems, such as battery status, thermal information, and cooling device
status.

## Version 1.8

- **Build system**: Autotools (configure + make)
- **Compiler**: clang/clang++ on HarmonyOS aarch64
- **License**: MIT
- **Homepage**: https://savannah.nongnu.org/projects/acpi/

## Build Notes

This build was compiled on HarmonyOS (OHOS) aarch64 platform with static linking.

### Patches Applied

- `0001-configure.patch`: Bypass HMDFS mktemp permission issue by replacing
  `mktemp -d` with `false`, falling through to the `mkdir` fallback path.

### Additional Source Modifications (in conanfile.py)

- `main.c`: Fixed `version()` and `usage()` functions to `return 0` instead of
  `return 1`, conforming to POSIX expectations for `--version`/`--help` exit codes.

## Dependencies

None — acpi is a self-contained command-line tool with no third-party library
dependencies.
