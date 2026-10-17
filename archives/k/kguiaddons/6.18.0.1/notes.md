# kguiaddons 6.18.0.1 notes

## 修订原因（相对 6.18.0）

- **共享库缺 SONAME（根因）**：Conan 的 `HarmonyOS` 系统名在 CMake 里没有平台模块
  （构建日志里可见 `System is unknown to cmake, create Platform/HarmonyOS`），
  `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 因此为空 ⇒ 产出的
  `libKF6GuiAddons.so` **没有 SONAME**（真机 `llvm-readelf -d` 实测 SONAME 命中 0）。
  消费者（kcolorscheme / kconfigwidgets / libkleo / ktextaddons）链接它之后，
  `DT_NEEDED` 里记的是**绝对路径**（如 CI 上的
  `/storage/Users/currentUser/.cache/conan2/p/b/kguia5c3aa78c951c4/p/lib/libKF6GuiAddons.so`），
  测试运行期该路径不存在 ⇒ `Error loading shared library ... (needed by .../libKF6ColorScheme.so)`
  ⇒ 下游 `KColorUtils*` / `KColorSchemeWatcher*` 等符号全部解析失败，凡链接它的用例一起红。
- **本修订**：在 OHOS 上改用 CMake 的 OHOS 平台规则
  （`cmake_system_name=OHOS`）并注入 SONAME/rpath flag
  （`_configure_ohos_shared_library_rules`，与 `knotifications/6.18.0.1` 同法）。
- **打包期 ELF 自签名**：OHOS 只加载带有效 `.codesign` 段的 ELF，而
  `CMake.install()` 把库**复制**进包目录会破坏签名 ⇒ 消费者运行期
  `Error loading shared library <绝对路径>/libKF6GuiAddons.so`。
  `package()` 现在对包内所有 ELF 重新
  `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` + `chmod 755`。
- **qtbase pin 对齐**：`qtbase/6.11.1` → `qtbase/6.11.1.3`（已发布）。本包只有一条
  qtbase 边，**不加** `override=True`（加了反而会让它不进依赖集而 KeyError）。

## Scope（与 6.18.0 相同）

This package is part of the Akonadi KF 6.18 baseline and keeps the
`KF6::GuiAddons` library surface available to downstream packages.

## Adaptations（与 6.18.0 相同）

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `WITH_WAYLAND=OFF` and `WITH_X11=OFF` avoid desktop-session integrations and
  unavailable Qt/Wayland/X11 dependencies.
- `USE_DBUS=OFF` avoids Qt6DBus until the shared Qt DBus baseline lands.
- `BUILD_PYTHON_BINDINGS=OFF` avoids Shiboken6/PySide6.
- `BUILD_GEO_SCHEME_HANDLER=OFF` skips the optional geo URI desktop handler.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- CMake configure/build prepends the OHOS SDK `native/llvm/lib` directory to
  `LD_LIBRARY_PATH` so SDK `lld` can load its matching `libxml2.so.16` on CI
  workers that do not export that path globally.

## Verification

- 6.18.0（已发布）：真机 `conan create` 通过，上游 CTest 8/8、`test_package` 1/1。
- 6.18.0.1：待真机 `conan create` 复验，重点检查
  ①`llvm-readelf -d libKF6GuiAddons.so | grep SONAME` 命中
  ②`Signed N OHOS package ELF file(s)` ③上游 CTest 与 `test_package` 通过。
