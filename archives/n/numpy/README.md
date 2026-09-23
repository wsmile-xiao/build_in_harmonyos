# numpy 1.26.4

## Overview

[numpy](https://numpy.org/) is the fundamental package for array computing
in Python. It contains a C/Python extension built via meson-python.

**Type**: Python C-extension package (meson build) — this is a Python
package, not a plain C/C++ library.

## Source

- PyPI sdist `numpy-1.26.4.tar.gz`
- SHA256 `2a02aba9ed12e4ac4eb3ea9421c420301a0c6460d9830d74a9df87efa4912010`

## Build notes (OHOS)

See `archives/n/numpy/1.26.4/conanfile.py` comments: Cython<3.1 +
meson-python<0.16 + system ninja; explicit AR via `llvm-ar`, `NINJA`
env var injection; test uses local Python (`PyType_IsSubtype`).

## Runtime

No hard deps; C extension `.so` installed in site-packages.

## License

BSD-3-Clause