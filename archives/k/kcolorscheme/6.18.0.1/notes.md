# kcolorscheme 6.18.0.1 适配笔记

## Scope

kcolorscheme 6.18.0.1 是 KF 6.18 基线包，配合 alligator 依赖图发布。
版本号 6.18.0.1 是适配修复后缀（R37）：已发布的 kcolorscheme/6.18.0 精确锁定
ki18n/6.18.0，而下游 alligator 需要 ki18n/6.18.0.1（BUILD_WITH_QML=ON，
提供 KF6::I18nQml），因此发布 6.18.0.1 配套。conandata.yml sources 指向
上游官方 6.18.0 tarball（SHA256 与已发布 6.18.0 完全一致）。

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` 绕过 KDE 平台 allowlist（OHOS 不在其中）。
- `KF_SKIP_PO_PROCESSING=ON` 跳过翻译目录生成（下游只需 KF6::ColorScheme 库）。
- `BUILD_TESTING=ON` 构建并运行上游 CTest/autotests（kcolorschemetest）。
- 依赖对齐 localkf 配方：`qtbase/6.11.1`、`kconfig/6.18.0`、`kguiaddons/6.18.0`、
  `ki18n/6.18.0.1`，build 依赖 `ecm/6.20.0`。
- ECM_MODULE_PATH 手动设置（CMakeDeps 生成的 ECMConfig.cmake 不传递该变量）。
- conan_cmakedeps_paths.cmake 手动生成（qtbase 用 cmake_find_mode=none，
  CMakeDeps 不会把它的 lib/cmake 加入 CMAKE_PREFIX_PATH）。

## 上游测试（R51 三步法）

上游测试清点：autotests/ 目录 1 个 CTest 注册项 `kcolorschemetest`
（`autotests/kcolorschemetest.cpp`，用 ECMAddTests 的 ecm_add_test 注册）。

实测（本地 OHOS aarch64，clang 15，QT_QPA_PLATFORM=offscreen）：

```
ctest --output-on-failure --no-tests=error
1/1 Test #1: kcolorschemetest  Passed  0.63 sec
100% tests passed, 0 tests failed out of 1
```

通过率 100%（1/1），无失败项。

关键运行时细节：KF6 共享库记录构建树相对 DT_NEEDED
（libKF6ConfigGui.so 需要 ../../bin/libKF6ConfigCore.so），CTest 从
`<build>/autotests` 运行，../../bin 解析到 `<build>/../bin`；因此
`_prepare_ctest_runtime_links()` 需把每个依赖的 lib*.so* 符号链接到
`<build>/../bin` 兼容目录（conanfile.py 已内置）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 直接运行 `./bin/kcolorschemetest` 报 `Error loading shared library ../../bin/libKF6ConfigCore.so` | KF6 库 DT_NEEDED 是构建树相对路径，从进程 CWD 解析 | 用 ctest 运行（CWD 为 `<build>/autotests`），并建立 `<build>/../bin` 兼容符号链接农场 |
| 2 | conan-init 误判构建系统为 autotools | init 阶段无 configure 脚本启发式 | 手工按 CMake 项目重写 conanfile.py（复用 localkf + 6.18.0 归档配方） |

## 源码修改

无补丁（patches: {}）。无平台宏。

## 依赖版本

- qtbase/6.11.1
- kconfig/6.18.0
- kguiaddons/6.18.0
- ki18n/6.18.0.1
- ecm/6.20.0 (tool_requires)

## 验证结果

1. 手动模式 B 编译（cmake configure + make）成功，libKF6ColorScheme.so 生成。
2. 上游 ctest：1/1 通过（100%）。
3. conan-verify：8 道门禁（G0-G4 + L2/L4/L5）通过。
4. finish W3 本地 conan create 通过。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake + OHOS 适配配方（BUILD_TESTING=ON + ctest） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/ | KColorScheme 消费者冒烟（构造 KColorScheme 并验证背景画刷有效） |
---

**编译结束**: 2026-09-06 16:17
**最终状态**: published
