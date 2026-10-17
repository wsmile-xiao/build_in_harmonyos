# ld2410-ble

Async Python interface for Hi-Link LD2410 / LD2410B 24GHz human presence radar
sensors, layered on top of `bleak` (BLE GATT). Pure-Python library distributed as
a wheel and installed into the interpreter's `site-packages` — no compiled
extension, no C/C++ toolchain involvement.

## Homepage
https://github.com/930913/ld2410-ble

## License
Apache-2.0

## Build System
Poetry (PEP 517, `poetry-core` backend) — `pip install .` into a private prefix.

## Dependencies
- `bleak` >= 0.19.0 — async BLE GATT client (no Conan recipe published; resolved from the `pypi.cnb.cool` mirror, same route as `airthings-ble/1.2.0`)
- `bleak-retry-connector` >= 2.3.0 — resilient connect/retry wrapper (same mirror route)
- `async-timeout` >= 4.0.1 — timeout helper (`async-timeout/5.0.1`, published in the 制品仓)

## OHOS Adaptation
- **Zero source modification**: the upstream GitHub tag archive is used verbatim, `patches_applied: []`, no `patches/` payload.
- **Source = GitHub official tag archive (v0.2.0), not the PyPI sdist** — the sdist ships without `tests/`, and this recipe runs the upstream pytest suite, so the archive must contain the test tree.
- Installed into a private prefix (`lib/python3.12/site-packages`) and exposed to consumers through `package_info()`'s `PYTHONPATH` — the `airthings-ble/1.2.0` / `platformdirs/4.3.8` convention for Python packages.
- **HarmonyOS platform gap (documented, not patched)**: `platform.system()` returns `"HarmonyOS"`, while bleak's `get_default_backend()` accepts only `"Linux"` and raises `BleakError: Unsupported platform: HarmonyOS`. The library's parsing/decoding surface works, but the default BLE transport backend cannot resolve on HarmonyOS. Upstream is intentionally left untouched; see `notes.md` for the measured evidence.
- bleak's `dbus-fast` dependency is gated by the wheel marker `platform_system == "Linux"`, which is false on HarmonyOS, so pip skips it. The mirror does carry `dbus_fast-*-ohos_aarch64.whl`, but its tag does not match this environment's pip tag (`harmonyos_aarch64`). This is a dependency-metadata limitation, not a recipe choice.

## Versions
- 0.2.0 — built 2026-09-25 (pure Python; upstream pytest 1/1, consumer API 43/43, HarmonyOS-specific 20/20; local CI simulation W3 PASS)
