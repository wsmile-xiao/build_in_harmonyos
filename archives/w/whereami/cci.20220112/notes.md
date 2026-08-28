# whereami cci.20220112 adaptation notes

## Source and version

Upstream has no release tags. This recipe uses the Conan Center snapshot `cci.20220112`, pinned to official commit `f15606a65908bb097e1887a08a40ae083e9a5c53`.

## HarmonyOS adaptation

whereami selects its procfs implementation with `__linux__`. HarmonyOS PC provides the required Linux-kernel procfs interfaces but defines `__OHOS__`, so the recipe enables the upstream Linux implementation only for OHOS builds. The pinned snapshot's `/proc/self/maps` parser fails on OHOS arm64; the recipe uses the platform-provided `dladdr` for module lookup and retains upstream's procfs implementation for executable lookup.

The package is a library only and does not install command-line tools, so `commands.json` is not required.

## Tests

The pinned upstream snapshot contains examples but no automated tests or test target. The Conan consumer test loads a real shared module linked with whereami, calls both public APIs through that module, and validates length-query contracts, absolute paths, directory offsets, and expected executable/module file names.

During OHOS compilation, the recipe prepends the active SDK's `llvm/lib` directory so `lld` loads its ABI-matched `libxml2.so.16` instead of an incompatible ambient library. The test runtime environment remains unchanged.
---

**编译结束**: 2026-08-27 00:04
**最终状态**: built
