# libgravatar 25.12.3

## Scope

KDE PIM's Gravatar integration library (`KPim6Gravatar`), ported for HarmonyOS
PC from the official KDE 25.12.3 source archive. The existing `gravatar/25.12.3`
archive remains unchanged.

## Build configuration

- Conan dependencies: Qt 6.11.1, KDE Frameworks 6.18.0 dependencies, and ECM
  6.26.0 as a build tool.
- CMake uses C++20, enables upstream tests, disables QCH generation, skips
  translation compilation, and allows KDE's platform check to accept OHOS.
- The HarmonyOS-specific consumer test uses the public `GravatarCache` API,
  checks the device OS and cache path, then writes, reads, and removes a real
  temporary file in the cache directory.

## Upstream test census

The source registers six CTest autotests under `autotests/`. The separate
`tests/gravatarwidget_gui.cpp` program is interactive and is not registered
with CTest, so it is recorded as a GUI smoke program rather than included in
the automated test count.

## Verification

On 2026-10-14, `conan create` completed on the supplied HarmonyOS 6.0 aarch64
device with Clang 15.0.4 and the `ohos-aarch64` Conan profile. The upstream
CTest suite passed all 6 registered autotests. Conan's `test_package` built and
ran both consumer executables successfully:

1. `test_gravatar`: email accessors, backend/default-pixmap options, and image
   size defaulting/clamping.
2. `test_harmonyos_cache`: checked the HarmonyOS kernel identity, initialized
   `GravatarCache`, verified its data directory, and performed a real temporary
   file write/read/removal there.

The device's cached KDE dependency binaries contain absolute `DT_NEEDED` paths
into an older `.cache/conan2` location. For this run, a temporary compatibility
runner linked those paths to the matching active `.conan2` files and removed
the links on exit; no package source or dependency binary was modified.

## Implementation observations

- `GravatarResolvUrlJob::canStart()` also checks current network reachability.
  The consumer test therefore exercises deterministic property APIs and keeps
  Gravatar network access out of offline verification.
- The source's separate `tests/gravatarwidget_gui.cpp` is interactive and is
  not registered with CTest; automated coverage is the six registered
  autotests.

## Verification record

- Device Conan build and upstream CTest: passed, 6/6.
- Conan consumer package tests: passed, 2/2 on HarmonyOS 6.0 aarch64.
- Repository local CI W3 step: passed on HarmonyOS aarch64. L0, L1, L4 and L5
  passed; L2 was skipped because this library installs no executable under
  `bin/`.

The full finish workflow stopped at W5 because the repository-wide knowledge
graph already has missing fields in E219 (root_cause), E253 (root_cause), and
E305 (root_cause and rec_approach). These entries are unrelated to this
package. The package-specific knowledge check passed after recording the
network-dependent `canStart()` behavior outside the knowledge-discovery
section. No reusable knowledge graph entry was needed for this basic
adaptation.

### 对话 #1

用户确认采用基础适配路线，并要求在 HarmonyOS PC 上完成 aarch64 本地 CI、Conan 测试及至少一个实际鸿蒙特有测试。
