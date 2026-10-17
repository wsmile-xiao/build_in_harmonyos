# bambootracker 0.6.5 适配笔记

## 编译环境
- 构建系统: cmake（Qt6）
- 编译日期: 2026-08-27
- 编译器: clang/clang++
- 目标平台: HarmonyOS PC (aarch64)
- 状态: built（本地验证）

## 编译步骤
1. init-build 下载官方 GitHub releases 源码包，SHA-256 核验通过。
2. 依赖拓扑核验（ohpcd 制品仓均可消费）：
   - qtbase/6.11.1（Core/Gui/Widgets/Xml）
   - qt5compat/6.11.1（Core5Compat，BambooTracker 的 Qt6 分支 require core5compat）
   - qttools/6.11.1（LinguistTools，BambooTracker 用 qt6_add_translation 编译 .ts）
   - alsa-lib/1.2.16（内嵌子模块 RtAudio/RtMidi 的 ALSA 后端）
3. 编写 CMake+Qt6 conanfile.py（生成器自动生成的 autotools 模板错误，已改写）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 检测 build_system=autotools 生成错误配方 | 源码含 autotools 风格子文件误判 | 改写为 CMakeToolchain+Qt6 配方 |
| 2 | qt5-qtbase/5.15.2 配方为 -no-widgets 构建 | 该 Qt5 包不含 Widgets | 改用 Qt6 qtbase/6.11.1（含 widgets 组件） |

## 依赖版本
- qtbase/6.11.1
- qt5compat/6.11.1
- qttools/6.11.1
- alsa-lib/1.2.16

## 验证结果
- conan create / W3 本地构建验证（见 .ci-result.json 与构建日志）
- 鸿蒙特有冒烟测试 test_package/test.sh：offscreen 平台启动 BambooTracker 二进制

## 注意事项
- BambooTracker 为桌面 GUI（Qt6 Widgets），运行时需 Qt offscreen 平台插件或图形环境。
- 上游无 ctest 注册测试；RtAudio/RtMidi 内嵌子模块测试需真实音频/MIDI 设备，默认不构建。
---

**编译结束**: 2026-08-29 13:22
**最终状态**: built
