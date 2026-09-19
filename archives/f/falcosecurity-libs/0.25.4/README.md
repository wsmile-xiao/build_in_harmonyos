# falcosecurity-libs 0.25.4

HarmonyOS PC aarch64 Conan adaptation of the upstream Falco userspace libraries.

- Upstream: https://github.com/falcosecurity/libs/tree/0.25.4
- License: Apache-2.0
- Build system: CMake
- Package contents: `libscap`, `libsinsp`, event schema and bundled runtime libraries
- Target: OpenHarmony/HarmonyOS PC, `aarch64-linux-ohos`, Clang 15

The recipe builds the userspace libraries with Linux kernel driver, kmod, modern BPF and live-driver E2E targets disabled on OHOS. The official userspace and savefile tests are executed during `build()`, and `test_package` calls the public `scap` and `sinsp` APIs.

See `notes.md` and `manifest.yaml` for the exact test ledger, skipped upstream scope and device evidence.
