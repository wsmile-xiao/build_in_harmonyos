# openFPGALoader 1.1.1 adaptation notes

## Configuration

- Build the command-line programmer with the OHOS CMake toolchain.
- Enable the dependency-free Remote Bitbang, XVC client, and SVF backends.
- Disable USB, FTDI, udev, libgpiod, and hidapi-only CMSIS-DAP integration because those dependencies and host services are not published for HarmonyOS PC.

## Verification

- The consumer test executes `openFPGALoader -V` without attached hardware.
- The pinned `v1.1.1/LICENSE` is Apache License 2.0; its SHA-256 is
  `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`.
- The evidence is the upstream `v1.1.1` tag's `LICENSE` file:
  <https://github.com/trabucayre/openFPGALoader/blob/v1.1.1/LICENSE>.
- The recipe verifies the downloaded `LICENSE` against that exact SHA-256 and
  fails source preparation unless both `Apache License` and `Version 2.0` are
  present.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
