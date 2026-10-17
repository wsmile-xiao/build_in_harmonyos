# spidev 3.8 OpenHarmony adaptation record

## Basic information

- Software: spidev
- Version: 3.8
- Build system: setuptools / CPython extension
- Target: Linux or OHOS with the spidev kernel userspace API

## Build guidance

The package builds the upstream `spidev` CPython extension with `pip install --prefix`.
It requires Python headers plus Linux-compatible SPI headers such as
`linux/spi/spidev.h`.
The recipe injects OHOS profile compiler and shared-link flags into setuptools
through `CC`, `CFLAGS`, and `LDSHARED`. On OHOS, the package step re-signs the
built CPython extension `.so` files with the available OHOS signing tools.

## Known limits

This module is a userspace binding for `/dev/spidev*` and `SPI_IOC_*` ioctls.
The local Windows workspace can validate recipe syntax and Conan export only.
Full `conan create` and runtime transfer tests need an OHOS/Linux environment
with the required kernel headers and, for hardware transfer checks, an SPI
device node. Current OHOS CI validation proves build, package signing, and
static extension artifact shape. Direct Python import from the Conan cache under
`/storage/Users/currentUser` can still be blocked by HMDFS/SELinux `dlopen`
policy after signing; import validation must be run from a loadable HNP/system
Python path. Hardware SPI transfer completeness still requires manual
confirmation on an OHOS target exposing `/dev/spidev*` and supporting the
required ioctls.

## Verification

Verification performed:

- `python -m py_compile conanfile.py test_package/conanfile.py test_package/test_spidev.py test_package/test_spidev_static.py`
- `conan inspect .`
- `conan export .`
- `git diff --check -- archives/s/spidev`
- OHOS old-port `conan create` and import/API `test_package` passed. Hardware
  transfer tests were not run because the device did not expose `/dev/spidev*`.
- PR CI failures reviewed: #11432 was caused by a stale `-lpython3.12` link
  flag; later failures were caused by OHOS refusing to import a package-cache
  Python extension `.so` from HMDFS even after signing. The recipe now guards
  libpython linking, re-signs OHOS package extensions, and uses static artifact
  checks for OHOS CI.
