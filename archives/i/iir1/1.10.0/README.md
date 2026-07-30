# iir1 1.10.0 for OpenHarmony PC

This directory provides the Conan recipe for upstream iir1 1.10.0.

```bash
conan create . -o 'iir1/*:shared=True'
conan create . -o 'iir1/*:shared=False'
```

The package exports CMake target `iir::iir` and pkg-config name `iir`. It has
no third-party Conan dependencies. The recipe builds all eight upstream tests;
`test_package` adds 46 independently executable consumer API commands across
Butterworth, Chebyshev I, Chebyshev II, RBJ, and invalid-parameter behavior.
The resulting logical total is 54; shared/static reruns are not double-counted.

Related work:

- Dependency Issue #1246
- Downstream DOSBox Staging Issue #1093
- Reusable knowledge drafts `E224`, `E228`, `E236`, and `E239`, submitted with this software
- Existing knowledge E050, E092, E207, and in-flight E217
