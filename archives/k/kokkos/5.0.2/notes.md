# Kokkos 5.0.2

- Builds the static C++20 Serial backend without external dependencies.
- Compiles the complete upstream unit-test configuration and executes every
  registered CTest on native targets.
- Routes GoogleTest temporary files to the writable build tree for restricted
  native runtimes where `/tmp` is unavailable.
- Uses Desul's portable compare-and-swap fallback for floating-point atomic
  add/sub after direct compiler builtins lost updates in native OHOS tests.
- License provenance: the official 5.0.2 source archive root `LICENSE` starts
  with "Kokkos is under the Apache License v2.0 with LLVM Exceptions"; that
  file has SHA-256 `c12f32e613739e0207af038b17b4caba7d6299263dadfe85272396c114ee35d4`.
- Cross builds deliberately do not execute target binaries on the host.
- The consumer performs a real `parallel_reduce` and verifies the sum.
- Official OHOS test and CI results remain pending.
