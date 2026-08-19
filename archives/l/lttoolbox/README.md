# lttoolbox

Apertium letter transducer toolbox — finite-state transducer library for
dictionary compilation and text processing. Core dependency of the
Apertium machine translation platform.

The package installs `liblttoolbox.a` (static library) plus the
`lt_comp` / `lt_proc` / `lt-expand` binaries under `bin/`.

Built with autotools on OHOS using clang 15 + libc++ + C++17, linking
ICU, libxml2, boost, and utfcpp. `apertium` 3.9.12 declares
`lttoolbox/3.7.6` as a `transitive_headers` dependency because
`lttoolbox/ustring.h` exposes ICU and utfcpp in its public headers.
