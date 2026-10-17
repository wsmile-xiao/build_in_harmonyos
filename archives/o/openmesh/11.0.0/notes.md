# OpenMesh 11.0.0 adaptation notes

- Source: official RWTH Aachen OpenMesh `11.0.0` release archive.
- Source SHA-256: `c7f35d29673e6dbb6d65b214c10c4c6249521a8f1e8f8db6e8bdc2eed798aedc`.
- No source patch is applied.
- Applications and documentation are disabled for the production package.
- On non-Windows platforms, upstream builds shared and static variants
  together. For the default static Conan option, the recipe packages the
  upstream `OpenMeshCoreStatic` and `OpenMeshToolsStatic` outputs under their
  canonical library names and propagates the upstream-required
  `OM_STATIC_BUILD` consumer definition so IO reader/writer modules register.
- The exact source contains 357 active GoogleTest source macros. With Eigen
  enabled, each of the three registered executables (`unittests`,
  `unittests_customvec`, and `unittests_doublevec`) runs 356 tests, for 1068
  actual case executions. These test-only builds use GoogleTest and Eigen and
  are validated outside the production Conan package.
- The consumer test covers triangle construction, face normals, OFF
  serialization/deserialization, and a missing-file fault path.
