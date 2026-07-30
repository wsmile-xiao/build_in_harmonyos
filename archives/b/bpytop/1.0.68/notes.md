# bpytop 1.0.68 OHOS adaptation notes

## Build approach

- Source package: official GitHub tag `v1.0.68`.
- Runtime dependency: pinned `psutil` 5.9.8 source package from PyPI.
- Packaging: compile psutil's Linux and POSIX C extensions directly with the
  Conan-configured compiler, then copy the real psutil Python modules, bpytop
  script, and themes into the package. This avoids a setuptools dependency and
  does not link against the host Python library.
- Entry point: `bin/bpytop` wrapper resolves the package-local Python
  site-packages path before executing `bpytop.py`.
- The wrapper keeps the package-local `site-packages` path by default. It only
  stages psutil to another location when `BPYTOP_RUNTIME_DIR` is explicitly set,
  avoiding CI temp/cache directories that reject native `.so` loading.
- The packaged psutil native extensions are installed with executable load
  permissions and are re-signed on OHOS after conditionally removing a stale
  `.codesign` section when present, so the HarmonyOS loader can map them.
- The non-interactive `--version` path is handled before terminal-only module
  validation, while still requiring and reporting the packaged psutil runtime.
  Interactive startup continues to require the upstream terminal modules.

## Verification

- Verified source and dependency sha256 values.
- The test package runs bpytop's upstream version command and verifies that the
  packaged native psutil extensions can read real CPU, memory, disk, and process
  data. The psutil runtime probe first validates the installed package path and
  only falls back to copied staging directories that pass an actual import probe.
- Linux x86_64 Release `conan create` passes with the packaged application,
  native psutil probes, and the missing-`termios` fault-injection check.
