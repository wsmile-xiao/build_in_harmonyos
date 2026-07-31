# spidev 3.8 adaptation notes

## Environment

- Build system: setuptools / CPython extension
- Date: 2026-07-28
- Status: built

## Build flow

The Conan recipe downloads the PyPI source distribution and builds the
`spidev` CPython extension using:

```bash
python -m pip install --break-system-packages --no-deps --prefix=<build_stage> <source_folder>
```

The package exposes the installed site-packages directory through `PYTHONPATH`
for build and run environments. The recipe passes OHOS profile compiler and
link flags to setuptools. On OHOS it avoids an explicit `libpython` link target
and lets the importing interpreter resolve Python C API symbols; this avoids
binding the packaged extension to the CI worker's HNP Python runtime while also
avoiding a bare `-lpython3.12` when sysconfig points at a directory that does
not contain the shared library.

## Platform findings

| # | Finding | Impact | Handling |
|---|---------|--------|----------|
| 1 | The extension includes `linux/spi/spidev.h`, `linux/types.h`, `linux/ioctl.h`, and `sys/ioctl.h`. | Windows local builds are not representative and should not be used as acceptance evidence. | Recipe validation allows only Linux and OHOS. |
| 2 | Runtime access uses `/dev/spidev*`, `/sys/module/spidev/parameters/bufsiz`, and `SPI_IOC_*` ioctls. | Import/API checks do not prove hardware transfer support. | Hardware SPI transfer completeness requires manual confirmation on an OHOS target with an SPI device node. |
| 3 | CPython extension packages are tied to the target Python ABI. | Build and consumption should use the same target Python major/minor version. | `PYTHONPATH` is computed from the active Python major/minor version. |
| 4 | setuptools extension builds need the same sysroot/link flags as direct compiler recipes. | Relying on Python sysconfig alone can lose OHOS profile flags. | The recipe injects `CC`, `CFLAGS`, and `LDSHARED` from Conan profile conf; on OHOS it avoids explicit `libpython` linkage and lets the importing interpreter provide Python C API symbols. |
| 5 | The OHOS Python environment may have pip but no importable `setuptools`. | `--no-build-isolation` fails at `Cannot import 'setuptools.build_meta'`. | Keep pip build isolation enabled and set `TMPDIR` to the Conan build directory. |
| 6 | OHOS rejects unsigned or stale-signed ELF shared objects during `dlopen`, and CI package paths under `/storage/Users/currentUser/.conan2` can still be blocked by HMDFS/SELinux after signing. | `import spidev` from the Conan cache can fail with `Error loading shared library ... Permission denied` even after `binary-sign-tool` adds `.codesign`. | During `package()`, OHOS Python extension `.so` files are re-signed from an original copy. OHOS `test_package` verifies the signed ELF artifact statically (`ELF`, `PyInit_spidev`, `.codesign`) instead of treating the HMDFS cache path as a universal loadability oracle. |

## Upstream tests

The PyPI 3.8 sdist was inspected on the old-port OHOS host. It contains
`spidev_module.c`, packaging metadata, README and CHANGELOG, but no `tests/`,
pytest/unittest entry, or example script that acts as a deterministic test.
The official upstream test count is therefore 0/0. Runtime SPI transfer checks
require a real `/dev/spidev*` node and are recorded as optional hardware
verification, not upstream sdist tests.

## Verification

Local preflight completed on the workspace branch:

```bash
python -m py_compile archives/s/spidev/3.8/conanfile.py archives/s/spidev/3.8/test_package/conanfile.py archives/s/spidev/3.8/test_package/test_spidev.py archives/s/spidev/3.8/test_package/test_spidev_static.py
conan inspect archives/s/spidev/3.8
conan export archives/s/spidev/3.8
git diff --check -- archives/s/spidev
```

Latest local export after the CI #11629 fix:
`spidev/3.8#09a2442e4d883f6659d788d983e65fc5`.

CI failure analysis:

- PR CI #11432 failed while linking the wheel because `LDSHARED` contained a
  bare `-lpython3.12` but the CI worker did not provide `libpython3.12` in the
  advertised sysconfig library directory. The recipe now avoids explicit
  `libpython` linkage on OHOS and relies on the importing interpreter for
  Python C API symbols.
- PR CI #11467 built and packaged the wheel, then failed in `test_package` at
  `import spidev` with `Error loading shared library ... Permission denied`.
  This matches the known OHOS ELF loading requirement for user-built shared
  objects; the recipe now re-signs package `.so` files during `package()`.
- PR CI #11510 still reached `Signed OHOS Python extension`, but `import spidev`
  failed with the same loader `Permission denied`. The signing step now prefers
  `$HOME/usr/local/bin` signing tools before the profile compiler directory.
- PR CI #11544 showed `_sign_elf` could still fail during package-time loading
  with `Permission denied`. The recipe keeps OHOS extension linkage independent
  of the CI worker's mapped `libpython`.
- PR CI #11580 built and installed the wheel, then failed in `package()` after
  `/data/service/hnp/bin/binary-sign-tool` produced a signed extension that the
  Python import loader still rejected with `Permission denied`. The signing
  routine now preserves the original `.so`, uses the `llvm-objcopy` paired with
  each signer when available, tries `-signAlg SHA256withECDSA` before the
  default `-selfSign 1` command, and reports every signer/variant failure
  instead of keeping only the last error.
- AI review on 2026-07-30 also flagged the OHOS missing-signing-tool branch.
  The recipe now fails package generation when `llvm-objcopy` or
  `binary-sign-tool` cannot be found, rather than silently producing an unsigned
  OHOS extension.
- PR CI #11629 ran recipe revision `4adf6604cc86e52560e9a6e1e2144582` and
  proved the remaining failure was not a missing tool or link failure: the wheel
  built successfully, `/data/service/hnp/bin/binary-sign-tool` signed the
  extension with both `-signAlg SHA256withECDSA` and the default self-sign mode,
  yet Python still rejected the extension from
  `/storage/Users/currentUser/.conan2/.../site-packages` with
  `Permission denied`. This matches the known HMDFS/SELinux load policy for
  Python/XS extension `.so` files in user storage. The package step therefore
  now requires signing command success, while OHOS `test_package` performs
  static artifact checks for ELF format, `PyInit_spidev`, and `.codesign`;
  actual import validation remains tied to deployment in an HNP/system Python
  path with a loadable SELinux label.

Pending verification:

- Manually confirm hardware SPI transfer on an OHOS target exposing
  `/dev/spidev*` and supporting the required `SPI_IOC_*` ioctls.

OHOS old-port verification completed:

- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-spidev-spidev-3.8-conan-r4-oldport-test-api-20260730-061708-26799`
- Full ref: `spidev/3.8#e40a7f3161fb10b9c7a628d0f4fb6311:01d92cf349a0dd98ff915f4bd99a04430171517f#d319e84692fbff6330c583ffaddc66c2`
- L0: pass. L1: pass (`test_package` imports extension and checks API shape). L2: skip (`spidev` has no `bin/`). L4: pass (no patches). L5: pass (`lib/` has content). L1e: pass.
- Upstream tests: 0/0 because the PyPI sdist ships no test suite.
- Hardware transfer tests: not executed because the old-port device has no `/dev/spidev*` node and no readable `/sys/module/spidev/parameters/bufsiz`; that old-port validation covered compile/import/API smoke only.
- Current CI workers differ from that old-port run: PR CI #11629 only used the
  `/data/service/hnp/bin` signer and still rejected Conan-cache imports after
  signing, so the automated OHOS CI validation is now build/sign/static artifact
  verification rather than cache-path import.
