# 预分析报告: qtspeech 6.11.1

> 生成日期: 2026-08-14
> 官方源码: https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtspeech-everywhere-src-6.11.1.tar.xz
> SHA256: `c035c318012025875a653245701a23d3807e8e46b8bf7987877842219c273f14`

## 1. 构建系统

- CMake，使用 Qt `BuildInternals` 构建模块。
- 必需依赖：`qtbase/6.11.1`、`qtmultimedia/6.11.1`，均已在 OHPCD Conan 制品仓发布并存在 OHOS armv8 Release 二进制。
- 可选依赖：`qtdeclarative/6.11.1`，当前未发布；核心 C++ 模块不要求该依赖，关闭 QML 构建。

## 2. 平台与后端分析

- 核心 `QtTextToSpeech` 库仅要求 Qt Core。
- 上游始终构建 mock TTS 插件，可用于无原生语音服务平台的 API 与状态机测试。
- Speech Dispatcher 后端仅在找到 `speech-dispatcher` 时构建；HarmonyOS 当前不提供该依赖，应显式关闭。
- Flite 后端仅在找到 Flite 时构建，并依赖 Qt Multimedia Private；当前任务不引入 Flite，应显式关闭。
- Android、Darwin、SAPI、WinRT 后端均有平台条件，不应在 HarmonyOS 构建。
- 上游示例依赖 Widgets 或 Qt Quick；不是核心库和消费者验证的必要部分，应关闭示例。

## 3. 图形与音视频

- 核心库不直接要求 X11、Wayland、OpenGL 或 ArkUI。
- 当前 `qtbase/6.11.1` 为无 XCB/OpenGL 的 raster Gui/Widgets 构建，但核心模块预计不依赖显示服务。
- 没有 HarmonyOS 原生 TTS 后端；初始适配以核心库和 mock 插件为范围，不宣称具备真实语音合成能力。

## 4. 测试计划

- 构建上游 `tst_qvoice` 与 `tst_qtexttospeech` 测试。
- 使用上游 mock 插件运行 `QTextToSpeech` 的引擎发现、locale、voice、rate、pitch、volume、state 与错误处理测试。
- Conan `test_package` 必须链接 `Qt6::TextToSpeech`，显式使用 `mock` 引擎并执行真实 API 调用；不得仅检查文件或打印固定字符串。

## 5. 预期配置

- `QT_BUILD_TESTS=ON`
- `QT_BUILD_TESTS_BY_DEFAULT=OFF`
- `QT_BUILD_EXAMPLES=OFF`
- `FEATURE_speechd=OFF`
- `FEATURE_flite=OFF`
- 不提供 `qtdeclarative`，从而跳过 QML 模块和 QML 测试。

## 6. 风险与结论

- Qt 模块需要正确发现 Conan 提供的 Qt BuildInternals、host tools 和私有 CMake API。
- 上游 mock 插件必须被正确安装并在测试运行时通过 Qt plugin path 发现。
- HarmonyOS 缺少原生 TTS 服务属于已知功能限制，不影响核心 API 与 mock 后端适配，但必须在报告和 PR 中明确披露。
- CMake MODULE 插件默认不生成 SONAME；HarmonyOS L5 门禁要求为 mock 插件显式添加相对 `DT_SONAME` 并修正导出的 imported-target 元数据。
- 当前未发现需要新增系统能力需求图谱条目的阻塞。
