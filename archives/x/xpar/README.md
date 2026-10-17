# xpar

`xpar` is a command-line error-correction and integrity tool. It can create
parity-protected archives, check their integrity, and recover damaged input
when the required parity data is available.

The HarmonyOS aarch64 package is available as Conan reference `xpar/1.1` and
provides the executable `bin/xpar`. This version uses the upstream AArch64
optimizations and disables optional Linux-only io_uring support.

Upstream project: <https://github.com/iczelia/xpar>

License: GPL-3.0-or-later.
