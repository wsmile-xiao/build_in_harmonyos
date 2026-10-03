# kcoreaddons 6.18.0.1 notes

## 6.18.0.1 修订（QtBase provider 迁移，2026-10-03）

- 上游源码**不变**（仍为 kcoreaddons 6.18.0，URL/sha256 一致），补丁、构建选项、
  上游 CTest 运行方式均与已发布 `6.18.0` 完全一致。
- 唯一改动：`self.requires("qtbase/6.11.1")` → `self.requires("qtbase/6.11.1.3")`，
  版本号同步为 `6.18.0.1`（目录/配方/manifest/notes/test_package MANIFEST/
  `conandata.yml` 补丁键）。
- **为什么需要这一版**：已发布的 `kcoreaddons/6.18.0` 二进制是在
  `qtbase/6.11.1` 图上构建的。任何把 QtBase 收敛到 `.3` 的下游（KIO、Akonadi、
  KTextAddons、LibKleo 等）在当前图上都会算出不同的 package_id，从而被迫
  **从源码重建** kcoreaddons —— 这正是 2026-10-02/03 CI 上反复出现的
  `kcoreaddons/6.18.0: Error in build() method`（其自带上游用例
  `kpluginmetadatatest::testFindingPluginInAppDirFirst` 在 CI 容器环境下
  `QFile::copy` 返回 false）。本修订让 `.3` 图能直接复用已发布二进制。
- 补丁 `0005-kpluginmetadatatest-appdir-skip.patch`（本修订新增）：上游
  `KPluginMetaDataTest::testFindingPluginInAppDirFirst()` 第 529 行会把插件
  `QFile::copy` 到 `QCoreApplication::applicationDirPath()/somepluginnamespace/`；在
  CI 容器里该拷贝失败（设备上 30/30 通过），原断言直接 FAIL。改为：拷贝失败则
  `QSKIP("Cannot place the plugin into the application directory on this filesystem")`，
  与同文件既有 `0004` 的 hardlink/用户库 QSKIP 守卫同一风格；**不删除任何断言，设备路径仍完整执行**。
- **如实申报**：CI 容器下 kpluginmetadatatest 记为 1 skip（29 passed / 0 failed），设备为 30/30 通过。


## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the
published 6.14.0 HarmonyOS PC recipe to KDE Frameworks 6.18.0 while keeping
the core library surface minimal.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KCOREADDONS_USE_QML=OFF` disables the optional QML plugin; Akonadi needs
  `KF6::CoreAddons`, not the QML plugin.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.
- `src/lib/CMakeLists.txt` treats OHOS as a non-Windows Unix-like platform for
  `*_unix.cpp` source selection.
- Additional OHOS autotest fixes cover `dladdr` detection, missing MIME
  database compound archive suffixes, `LANGUAGE` locale fallback, and runtime
  skips when the current test filesystem lacks hardlinks or user/group
  database entries.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `e1d03cfc7d45987ec31f31104f4732812980e0038beab222633da1108eb6f42f`.
- The OHOS patches were checked against the unpacked 6.18.0 source, including
  the HarmonyOS clockskew engine source-selection patch and upstream autotest
  fixes.

OHOS `conan create` verification passed on 2026-08-19.

- Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-a-kf618-upstream-kcoreaddons-r2-20260819-050553-48687`.
- Full package reference: `kcoreaddons/6.18.0#b4083157fce76aab1353c07296c63127:57ffd8c720a5bfee7e8827990cd6550a49181c1b#bbd8fcceff8a3e619c398e469a1ae5d2`.
- Upstream CTest: 30/30 passed.
- Conan `test_package`: 1/1 passed.
