# cexception

## 1.3.4

CException is a small C exception-handling library based on setjmp/longjmp.
This archive packages the upstream lib/CException.h API and a static
libcexception.a built with the upstream Meson project on an OpenHarmony PC
aarch64 device.

- Upstream: https://github.com/ThrowTheSwitch/CException
- License: MIT
- Conan reference: cexception/1.3.4
- Build system: Meson
- Package form: static library

The upstream Meson files define static_library() but no install rules. The
Conan recipe therefore stages the verified library, public header, and license
explicitly. The recipe also rebuilds Meson's thin archive as a self-contained
archive before packaging.
