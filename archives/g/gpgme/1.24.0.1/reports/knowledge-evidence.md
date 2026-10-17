# GPGME 1.24.0.1 knowledge-extraction evidence

## Source baseline

- Original dependency-library PR: #7424.
- Source baseline recorded from the remote PR before this local extraction: `8787bcfc7a7878e530138e2795b3513d8965c12c`.
- Upstream source: `gpgme-1.24.0.tar.bz2`, SHA256 `61e3a6ad89323fecfaff176bc1728fb8c3312f2faa83424d9d5077ba20f5f7da`.

## Extracted mechanism

`_write_relocatable_cmake_configs()` creates `gpgmeConfig.cmake`, `GpgmeppConfig.cmake`, and `QGpgmeQt6Config.cmake` below `lib/cmake`. Every generated config computes the installed prefix from `CMAKE_CURRENT_LIST_DIR`, avoiding upstream absolute `/lib` and `/include` paths left after `DESTDIR` installation.

The exported target graph is:

```text
gpgme::gpgme -> libassuan::libassuan, libgpg-error::libgpg-error
Gpgmepp -> gpgme::gpgme
QGpgmeQt6 -> Gpgmepp, Qt6::Core
```

The test package discovers all three configs, links all three targets, then checks the C API, initializes the C++ API, and takes the Qt6 `QGpgME::openpgp` symbol address.

## Evidence boundary

- Static source inspection is current extraction evidence.
- `notes.md` and `manifest.yaml` record a historical CTest `1/1` and direct smoke result, but their raw runner log has not been rebound to the PR source baseline here.
- Upstream inventory is 45 tests: 3 C, 21 Qt5, and 21 Qt6. The package deliberately executes none because the suite requires an OHOS-unpublished GnuPG runtime.
- No device run, package-copy relocation experiment, or current CI run is claimed by this report.

## Required follow-up before accepting a general rule

1. Rerun `conan create` on the current PR HEAD and preserve the raw build/test logs.
2. Copy the installed package to a second prefix and rerun the consumer using each of the three CMake configs.
3. Reconcile the PR body with the exact `0/45` upstream inventory and separate it from any consumer result.
