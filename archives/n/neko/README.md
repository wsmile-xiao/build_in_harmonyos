# Neko

Neko is a lightweight virtual machine, bytecode compiler, and runtime used by
the Haxe ecosystem. This package installs the `neko`, `nekoc`, and `nekotools`
commands together with the public C API and shared library.

## OpenHarmony adaptation

- The bundled BoehmGC 7.6.16 dependency is built with CMake because its legacy
  autotools platform detection does not recognize HarmonyOS.
- Optional integrations that are not required by the core VM are disabled.
- Thread cancellation and ELF program-header support are selected by CMake
  capability checks instead of platform macros.
- Build-tree executables find `libneko` in the same output directory; installed
  executables use `$ORIGIN/../lib`.

## Dependencies

- zlib 1.3.1
- bundled BoehmGC 7.6.16 and libatomic_ops 7.6.14

## Verification

The recipe runs the four upstream CTest entries and a consumer test that links
the installed C API. The consumer test also runs `neko -version`.

## References

- https://nekovm.org
- https://github.com/HaxeFoundation/neko
