# Cgl 0.60.10 Adaptation Notes

## Build

Cgl uses the COIN-OR Autotools build. The recipe configures and builds in the
source directory because the recursive configure layout is not compatible with
the HMDFS VPATH build layout.

## Dependencies

- `coinutils/2.11.13`
- `coin-or/0.108.12` (Osi)
- `clp/1.17.10`
- `zlib/1.3.1`

The dependencies are public and transitive because Cgl public headers and the
static archive expose the COIN-OR dependency closure to consumers.

## HarmonyOS Handling

- Configure explicitly uses `aarch64-unknown-linux-musl`.
- Autotools helper scripts have their executable bits restored for HMDFS.
- Build, test, and install run serially to avoid the HMDFS make jobserver FIFO
  limitation.
- `TMPDIR` and `TMP` are set to a writable directory under `HOME`.
- `config.status` is regenerated with a stable `conftmp` directory and
  `umask 022`, avoiding the HMDFS SGID and `umask 077` conflict.
- Cgl's Clp-dependent sources receive the Clp, Osi, and CoinUtils include
  directories explicitly. The static archive closure is supplied to configure.
- The source mirror is listed before GitHub because the true-device worker
  cannot reliably download from GitHub.

## Validation

The recipe runs the upstream `make check` and `make test` suites; the Conan
consumer test verifies three `CglParam` state changes. Validate the exact
committed revision on an OHOS aarch64 device before proposing it for review.
