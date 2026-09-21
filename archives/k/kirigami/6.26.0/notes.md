# kirigami 6.26.0 适配笔记

## 概览

- 软件：KDE Frameworks 6 · Kirigami（libkirigami6 + QML 模块 `org.kde.kirigami`）
- 版本：6.26.0
- 构建系统：CMake（Conan 2）
- 源码：`https://download.kde.org/stable/frameworks/6.26/kirigami-6.26.0.tar.xz`
- sha256：`b268785b271198acec7fe4b6177eafdee890e180245c7168916da3ccff1425ff`（与上游 `.sha256` 文件一致）
- 状态：`built`（新增 HarmonyOS 专项测试后 Conan G2 通过；PR #10787 待重新审查）

## 依赖

| 类型 | 依赖 | 说明 |
|------|------|------|
| required | qtbase/6.11.1 | Core/Gui/Concurrent + `Qt6GuiPrivate`（Qt6Gui ≥ 6.10 时顶层强制 `find_package`） |
| required | qtdeclarative/6.11.1 | Qt6 Qml/Quick/QuickControls2/QuickTest |
| required | qtsvg/6.11.1 | Qt6 Svg（顶层 `find_package(Qt6 ... Svg)`） |
| required | qtshadertools/6.11.1 | Qt6 ShaderTools（qsb 烘焙内置 shader） |
| build | ecm/6.26.0 | `find_package(ECM 6.26.0 REQUIRED NO_MODULE)` |

> 上游 kirigami 6.26.0 本体 **不** `find_package` kconfig / kguiaddons / ki18n：
> 这三个 KF6 模块只被 `templates/kirigami6/`（生成 App 的模板工程）与下游
> `kirigami-app-components` 使用，不是本框架的构建前置。

## 构建步骤

```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

关键 CMake 选项（`generate()`）：

- `BUILD_SHARED_LIBS=ON`、`BUILD_TESTING=ON`、`BUILD_EXAMPLES=OFF`、`BUILD_QCH=OFF`
- `DESKTOP_ENABLED=OFF`（桌面风格在 OHOS 上不需要，沿用 6.18.0 已验证配置）
- `USE_DBUS=OFF`（qtbase/6.11.1 不带 Qt6DBus；上游在非 UNIX 平台本就默认 OFF）
- `KF_IGNORE_PLATFORM_CHECK=TRUE`（HarmonyOS 不在 KDE 平台白名单）
- `KF_SKIP_PO_PROCESSING=ON`（ECM 6.26 的 `ECMPoQmTools` 尊重该开关，跳过需要 lrelease 的 po→qm 步骤）
- `CMAKE_CXX_STANDARD=20` / `configure()` 里 `self.settings.compiler.cppstd="20"`
- `CMAKE_BUILD_RPATH=$ORIGIN` + `CMAKE_EXE_LINKER_FLAGS=-Wl,--disable-new-dtags`
- OHOS 专用 soname/rpath 规则（`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` 等，经 `CMAKE_USER_MAKE_RULES_OVERRIDE_{C,CXX}` 注入）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `TypeError: get() got an unexpected keyword argument '6.26.0'` | `conandata.yml` 用版本键（`sources: {"6.26.0": {...}}`），而 `source()` 写成 `get(self, **self.conan_data["sources"])` | 改为 `self.conan_data["sources"][self.version]` |
| 2 | `no template named 'span' in namespace 'std'` / `no member named 'contains' in std::unordered_map` | 6.26 源码使用 C++20（`std::span`、`unordered_map::contains`、指定初始化器），但共享 profile `compiler.cppstd=17`；ConanToolchain 据此写出**非 cache** 的 `set(CMAKE_CXX_STANDARD 17)`，会遮蔽 `tc.variables` 的 cache 取值，且 ECM `KDECompilerSettings` 仅在 `if (NOT CMAKE_CXX_STANDARD)` 时才设 20，故实际编译为 `-std=c++17` | `configure()` 中 `self.settings.compiler.cppstd = "20"`（让 ConanToolchain 直接产出 `-std=c++20`） |
| 3 | 6.26 顶层 `find_package(Qt6GuiPrivate REQUIRED)` | `src/platform/CMakeLists.txt` 链接 `Qt6::GuiPrivate`；Qt6Gui 6.11.1 ≥ 6.10 触发 | qtbase/6.11.1 自带完整原生 Qt6 CMake 树（含 `Qt6GuiPrivateConfig.cmake`），以 `cmake_find_mode=none` + 前缀注入消费，无需额外包 |
| 4 | qsb 烘焙 shader 需要外部 `spirv-opt` | Qt 的 `OPTIMIZED` 选项调用 Vulkan SDK 的 `spirv-opt`，qtshadertools 未提供 | `source()` 阶段从 CMake 文件中剥除 `OPTIMIZED` 标记（不修改 tarball，无源码补丁） |
| 5 | OHOS 加载器把 DT_NEEDED 中的 `/` 当作 cwd 相对路径 | Kirigami QML 插件被链接为 `../bin/libKirigami*.so` | `package()` 安装后把 `../bin/libKirigami*.so` 改写为裸 soname，再用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign` 重新签名全部 ELF（E537 类） |

## 源码修改

无源码补丁（`patches/` 为空）。仅有两处配方内处理：
`source()` 剥除 `OPTIMIZED` shader 标记；`package()` 规范化 DT_NEEDED 并签名。

## 验证结果

- 上游测试（R51）：**N=38 注册 / N′=38 实跑 / 38 通过 = 100%**
  （`ctest --output-on-failure --no-tests=error`，无排除项；`tst_theme.qml` 亦通过：
  10 passed / 1 upstream-skip）
- test_package：ctest 2/2 + 消费者探针 3/3 + HarmonyOS 专项测试 1/1
  - `PASS: kirigami platform unit meta objects are exported`（C++ `Units`/`IconSizes`）
  - `PASS: installed QML module payload .../lib/qml/org/kde/kirigami contains qmldir and libKirigamiplugin.so`
  - `PASS: QQmlEngine imported org.kde.kirigami and instantiated Heading_QMLTYPE_7`（offscreen QPA）
  - `PASS: HarmonyOS HarmonyOS aarch64 runs Kirigami Units API`（`__OHOS__` 编译宏、`uname` 系统名/架构断言、Kirigami Units API）
- 安全基线（L4）：`GNU_RELRO` 存在，`GNU_STACK RW`（NX），`BIND_NOW` + `FLAGS_1 NOW`（full RELRO），ELF Type DYN / AArch64
- 产物基线（L5）：424 个文件；45 个 `lib/*.so*`；15 个 `qmldir`；16 个头文件；
  `KF6Kirigami` / `KF6KirigamiPlatform` / `KF6Kirigami2` CMake config 齐备；所有 ELF 均带 `.codesign`

## 交付物（安装进包）

| 路径 | 说明 |
|------|------|
| `lib/libKirigami*.so*` | 15 个 Kirigami 共享库（含 `libKirigami.so.6.26.0`） |
| `lib/qml/org/kde/kirigami/{qmldir,libKirigamiplugin.so,Kirigami.qmltypes}` | 主 QML 模块 `org.kde.kirigami` v2.0 |
| `lib/qml/org/kde/kirigami/{platform,layouts,primitives,templates,controls,delegates,dialogs,private,forms,styles}/` | 子 QML 模块 |
| `include/KF6/Kirigami/**` | 公共 C++ 头 |
| `lib/cmake/KF6Kirigami*` | `KF6::Kirigami` / `KF6::KirigamiPlatform` 消费目标 |

## 注意事项

- **下游 ki18n 缺口（不在本任务范围，仅记录）**：`ki18n/6.26.0` 的已发布配方设置
  `BUILD_WITH_QML=OFF`（自述 "Qt6 Qml module is not published to ohpcd"），因此发布包只含
  `lib/qml/org/kde/i18n/localeData`，**没有 `org.kde.ki18n` QML 模块**。kirigami 6.26.0 本体
  不需要它，但下游 `kirigami-app-components` v1.0.1 的 `ecm_find_qmlmodule(org.kde.ki18n REQUIRED)`
  会因此失败——这是 ki18n 的前置缺口，需另行立项修复 ki18n 配方（本任务未自行修改 ki18n）。
- **R38**：本包为 library、无 `bin/`，故**不**添加软件级 `commands.json`。
- PR #10787 原先因鸿蒙特有测试数为 0 被规则审查拒绝；本次新增 `test_package/test_kirigami_harmonyos.cpp`，并在 CTest 与 Conan test() 中各执行一次。
---

**编译结束**: 2026-09-19 16:06
**最终状态**: built
