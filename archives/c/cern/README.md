# cern

CERN VDT (Vectorised Math) library, fast approximate transcendental functions.

- Upstream: https://github.com/dpiparo/vdt
- Version: 0.4.6 (tag v0.4.6)
- Build: CMake, zero external dependencies (build-time Python only)
- OHOS notes: disable SSE/NEON flags on aarch64, DIAG=ON for upstream tests, librt guard for HarmonyOS.
