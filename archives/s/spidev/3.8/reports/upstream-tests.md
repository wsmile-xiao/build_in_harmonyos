# spidev 3.8 upstream tests

Date: 2026-07-30

## Release test inventory

The PyPI 3.8 source distribution was inspected on the old-port OHOS host.
The archive contains:

- `spidev_module.c`
- `setup.py`, `setup.cfg`, `pyproject.toml`
- `README.md`, `CHANGELOG.md`, `LICENSE`
- package metadata under `spidev.egg-info/`

No `tests/`, pytest/unittest entry, tox/nox config, or deterministic example
test script is shipped in the source distribution.

## OHOS execution status

Official upstream tests: 0/0 (not provided in the sdist).

The Conan `test_package` imports the built extension, checks `__version__ == "3.8"`,
and verifies the `SpiDev` API shape without opening hardware. Real SPI transfer
checks require a device exposing `/dev/spidev*` and are treated as optional
hardware verification rather than upstream sdist tests.

Old-port verification:

- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-spidev-spidev-3.8-conan-r4-oldport-test-api-20260730-061708-26799`
- Full ref: `spidev/3.8#e40a7f3161fb10b9c7a628d0f4fb6311:01d92cf349a0dd98ff915f4bd99a04430171517f#d319e84692fbff6330c583ffaddc66c2`
- Result: L0/L1/L4/L5/L1e pass; L2 skip because no `bin/` directory is expected.
- Hardware probe: `/dev/spidev*` not present; `/sys/module/spidev/parameters/bufsiz` not readable.
