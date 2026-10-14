# tundra

Tundra 2 is an incremental build system with embedded Lua configuration.

- Upstream: https://github.com/deplinenoise/tundra
- Version: 2.17.1
- License: MIT (`COPYING`)
- Commands: `tundra2`, `t2-lua`, `t2-inspect`

The OHOS recipe uses the upstream POSIX build with `UNAME=Linux`, because the
native platform reports `HarmonyOS` and its Clang toolchain defines the Linux
and Unix feature macros that Tundra uses. It packages the upstream installation
layout under `bin/` and `share/tundra/`.
The device lacks the GNU `install` command, so the recipe copies those outputs
with Python while preserving executable permissions.

All 79 upstream cases run in `conan create`: 48 C++ GoogleTest cases, 20 Perl
functional cases across seven groups, and 11 Lua selftest cases. The assembly
scanner group uses the published NASM tool through a test-only `yasm` shim;
compiler scanner cases use `clang` through a test-only `gcc` shim. The test
launcher caps Tundra's own workers at two.
