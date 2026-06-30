# check-jsonschema

A JSON Schema CLI built on jsonschema. Provides a command-line tool and pre-commit hook
to validate JSON/YAML files against JSON Schema specifications.

## Features
- Validate JSON and YAML files against JSON Schema
- Support for remote schema URLs
- Built-in schema support for common services (GitHub Actions, Renovate, etc.)
- Pre-commit hook integration

## OpenHarmony (OHOS) Adaptation Notes

### ELF Signing
All Python .so extension modules (rpds, regress, charset_normalizer) require ELF signing
on HarmonyOS to be executable. Use `ohc-run.py sign-elf` to sign them.

### RPATH Resolution
The bundled libgcc_s libraries in `rpds_py.libs/` and `regress.libs/` directories have RPATH
set to `$ORIGIN/../rpds_py.libs`, but HarmonyOS's dynamic linker doesn't resolve `$ORIGIN`
RPATH correctly. The solution is to modify `__init__.py` of rpds and regress packages to
preload the bundled libraries using ctypes with `RTLD_GLOBAL` mode.

### Dependencies
- Python 3.14+ (via harmonybrew/cmd-pkgs)
- jsonschema >= 4.18.0
- rpds-py >= 0.25.0
- ruamel.yaml == 0.18.6
- regress >= 0.4.0
- requests < 3.0
- click >= 8

## Installation
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- check-jsonschema 0.28.4
```

## Verification
```bash
check-jsonschema --version
# Expected output: check-jsonschema, version 0.28.4
```
