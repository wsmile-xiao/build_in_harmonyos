# kcolorscheme 6.26.0 适配笔记

## 适配范围

本适配基于 KDE 官方 `kcolorscheme-6.26.0.tar.xz`，面向 HarmonyOS PC
aarch64、clang 15、libc++ 和 C++17。适配采用路径 A，不修改上游源码。

## W0/W0b 核验

- `qtbase/6.11.1`、`ecm/6.26.0`、`kconfig/6.26.0`、
  `kguiaddons/6.26.0` 和 `ki18n/6.26.0` 均可从 `ohpcd` 下载 recipe。
- 已核对历史归档 `archives/k/kcolorscheme/6.18.0`。历史 OHOS 真机验证
  通过 1/1 上游 CTest 和 1/1 Conan 消费者测试；其 CMake、ECM 路径及
  无头运行环境仍适用于 6.26.0。
- 6.26.0 将最低 Qt 版本提高到 6.9.0；当前 `qtbase/6.11.1` 满足要求，
  并提供 Qt 6.10 以后构建所需的 `Qt6GuiPrivate`。

## 上游测试清点（R51）

| 检查项 | 数量 | 证据 |
| --- | ---: | --- |
| `autotests/` 测试源文件 | 1 | `autotests/kcolorschemetest.cpp` |
| CTest 注册项 | 1 | `ecm_add_test(kcolorschemetest.cpp ...)` |
| 测试数据文件 | 1 | `autotests/kcolorschemetest.colors` |

注册的 `kcolorschemetest` 覆盖颜色方案构造基准、7 类颜色集的背景/前景/
装饰色读取，以及配置对比度读取。配方设置 `BUILD_TESTING=ON`，不删减或
改写该测试，并使用 `ctest --no-tests=error` 确保测试未注册时直接失败。

## HarmonyOS 适配

- `KF_IGNORE_PLATFORM_CHECK=TRUE` 允许 KDE Frameworks 在 OHOS 配置上构建。
- `KF_SKIP_PO_PROCESSING=ON` 跳过翻译目录处理，不影响 `KF6::ColorScheme`
  核心库和内置 Breeze 配色资源。
- 显式加入 ECM、Qt6、KConfig、KGuiAddons 和 KI18n 的 CMake、库及头文件
  搜索路径，兼容这些 Conan 包自带的 CMake 配置。
- 上游 CTest 使用 `QT_QPA_PLATFORM=offscreen` 和隔离的 XDG 目录运行，
  不依赖 Wayland、X11 或桌面会话。
- 无源码补丁、无 `__OHOS__` 空壳分支。`KColorScheme` 的颜色读取、
  `KColorUtils` 调用和资源加载均保留上游真实实现，满足 R40。

## 消费者测试

`test_package` 通过上游导出的 `KF6::ColorScheme` 目标链接，构造
`KColorScheme`，验证背景、前景、装饰色均有效，并检查对比度位于合法
范围，共 4 项行为断言。

## 本地验证边界

- 官方源码 SHA256 已核验：
  `74149a0379bd8bf6590d3c1f7f8c503665e0f3adafc2adbd44fc6bb764c969f1`。
- C/C++ 语言预检通过，识别为 CMake/C++ 工程。
- Conan 完整依赖图解析和依赖二进制安装成功，确认真实包中存在
  `Qt6GuiPrivate`、`KF6Config`、`KF6GuiAddons` 和 `KF6I18n` CMake 配置。
- `conan-verify` 的 G0、G1 通过；G2 成功下载官方源码并进入 CMake 配置，
  随后在 `project()` 阶段停止，因为 OHOS profile 指定的
  `/data/service/hnp/bin/clang` 与 `/data/service/hnp/bin/clang++` 在当前
  macOS 主机不存在。该失败发生在源码编译前，未产生目标产物。
- 当前主机也不具备 aarch64 OHOS 系统库和 OHOS ELF 运行环境。这不是
  测试跳过条件；提交前须由 HarmonyOS worker 实际运行 1 项上游 CTest
  和 1 项消费者测试，并据实更新通过率。
