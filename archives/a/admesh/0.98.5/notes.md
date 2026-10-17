# ADMesh 0.98.5 adaptation notes

The exact upstream tag includes Autotools input files but intentionally omits a
generated `configure` script, and it defines no upstream test target. To avoid
requiring `autoreconf` and keep the cross build deterministic, the Conan recipe
compiles the same six library sources and the `admesh` CLI directly with the
toolchain supplied by Conan.

The package exports `stl.h`, a static `libadmesh` library, and the CLI. The
consumer test links against the packaged library and validates normal-vector
calculation for a deterministic triangle. CLI runtime and invalid-input checks
are required on the HarmonyOS PC emulator before submission.
