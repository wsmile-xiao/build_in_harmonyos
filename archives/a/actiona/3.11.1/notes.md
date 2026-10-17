# actiona 3.11.1 探索编译诊断记录

## 结论（W0 依赖缺口，阻塞适配）

**actiona 无法在当前制品仓条件下编译**，configure 在第一步即失败：
`Failed to find required Qt component "LinguistTools"`（Qt6Config.cmake 存在但组件缺失）。

## 依赖缺口清单（制品仓 ohpcd 实测，conan download --only-recipe 验证）

| 依赖 | 需要的 Qt 组件 | 制品仓状态 |
|------|---------------|-----------|
| qtbase/6.11.1 | Core/Network/Gui/Widgets/Xml | ✅ 已发布（binary 可安装） |
| opencv/4.12.0 | core/imgproc | ✅ 已发布（binary 可安装） |
| qtdeclarative | Qml、QmlPrivate | ❌ Recipe 不存在 |
| qttools | UiTools、LinguistTools | ❌ Recipe 不存在 |
| qtcore5compat | Core5Compat | ❌ Recipe 不存在 |
| qtmultimedia | Multimedia、MultimediaWidgets | ❌ Recipe 不存在 |
| qttexttospeech | TextToSpeech | ❌ Recipe 不存在 |
| qtbase Sql/DBus 组件 | Sql、DBus（actions/data、actions/system 用） | ❌ qtbase binary 未含 |

## 证据

- configure: `By not providing "FindQt6.cmake"... could not find Qt6Config.cmake`（未设 CMAKE_PREFIX_PATH 时）
- 设 CMAKE_PREFIX_PATH=qtbase 包目录后：`Failed to find required Qt component "LinguistTools"`
- 制品仓全量 1234 个包 grep：qtdeclarative/qtmultimedia/qttools/qtcore5compat/qttexttospeech 均无
- actiona CMakeLists 全部子目录无条件 add_subdirectory，find_package 全部 REQUIRED，无裁剪选项
- 上游 CI（.github/workflows/linux.yml）也要求 qtmultimedia/qt5compat/qtspeech 模块 + libnotify/libxtst/libbluetooth/libudev

## 建议（按 SKILL W0/R36）

依赖未发布 → 停止当前适配，先按拓扑序适配并发布缺失的 Qt 模块
（qtcore5compat → qttexttospeech → qttools → qtdeclarative → qtmultimedia），
再回来适配 actiona。每个 Qt 模块为独立 PR（W2 原子性）。
---

**编译结束**: 2026-08-17 07:38
**最终状态**: built
