# kuroko/1.4.0 for HarmonyOS PC

Kuroko is a bytecode-compiled language with an embeddable C VM. This recipe
builds the official v1.4.0 release natively on HarmonyOS PC AArch64 with
Clang, preserving the default rich line editor. It packages the interpreter,
static and shared C libraries, headers, native extension modules, language
modules and upstream command-line tools.

The official release contains 148 paired `.krk`/`.expect` tests. The recipe
runs all 148 on the target before packaging. The Conan consumer then exercises
the installed interpreter, relative module lookup, an installed tool and the
shared-library C API from outside the source tree.

Upstream tools encode `$ORIGIN` as their runtime library path. In the Conan
layout the tools are in `bin/` and `libkuroko.so` is in `lib/`; therefore tools
must be run under the Conan run environment (which sets `LD_LIBRARY_PATH`) or
an equivalent caller-provided library path. The interpreter itself links the
static VM library and does not need that setting.
