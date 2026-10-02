# k3conf 0.3 HarmonyOS PC adaptation notes

- Upstream: TI `k3conf` tag `v0.3`, commit `de06befe878be061a40540d2127d4273320b35bc`.
- Build system: CMake; standalone C executable with no third-party runtime dependencies.
- Adaptation: use Conan's CMake toolchain, install the `k3conf` executable under `bin`, and apply one portability patch so `--version` does not probe `/dev/mem` on non-TI PCs.
- Tests: upstream v0.3 has no registered test suite. The Conan test package checks help output, version output, and the HarmonyOS AArch64 ELF header. Hardware-dependent commands are not run by CI.
## 最终状态

CI build #66557 passed compilation, packaging, Conan test_package, L0, and L1 on HarmonyOS AArch64. The three added assertions passed: `--help`, `--version`, and the OHOS ELF header check.
