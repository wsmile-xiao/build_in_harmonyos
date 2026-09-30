# rtmidi 6.0.0 适配笔记

## 软件信息

- 上游: <https://github.com/thestk/rtmidi>（实时 MIDI 输入/输出 C++ 库，
  跨 Linux(ALSA/JACK)/macOS(CoreMIDI)/Windows(MM/UWP)/Web/Android(AMIDI)）
- 版本: 6.0.0（release tag 6.0.0）；CMake ≥3.24（设备 SDK cmake 3.28.2 满足）
- 任务: ohpcd contrib-2590（领取时无人认领、无 PR 记录）

## 编译环境

- 真机: 10.195.180.238（隔离 job `device-b/rtmidi-kb-20260920`）
- 编译器: clang 15.0.4；Conan 2.29.1；状态: built

## 上游测试清点（R51 第 1 步）

| 清点项 | 结果 | 依据 |
|---|---|---|
| tests/ 内容 | 8 个示例程序 | cmidiin/midiclock/midiout/midiprobe/qmidiin/sysextest（交互演示）/apinames（真实断言）/testcapi（C API 冒烟） |
| ctest 注册 | 无（仅可执行目标） | CMakeLists 仅 add_executable |
| 可自动化项 | apinames + testcapi | build() 内运行 |
| 交互式演示不运行 | 需实时 MIDI 硬件/输入 | 无适用环境 |

## 适配要点

- OHOS 无任何 MIDI 后端 → 上游 RtMidi.cpp:88-90 自动 `#define __RTMIDI_DUMMY__`
  （“可编译但无功能”后端），无需补丁
- 验证契约：apinames 确认 dummy 在编译 API 列表且名称映射正确；
  消费者测试断言 dummy 行为契约（portCount=0、openPort no-op、sendMessage 不崩、
  非法 API 显示名 Unknown）

## 遇到的问题与解决方案（真机实测后回填）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首跑 apinames 空 API 列表 + testcapi SIGSEGV(exit 139) | 上游 rtmidi_compiled_apis[] 数组漏列 dummy 条目（自动回退宏生效但数组不含它）→ 默认构造无 API 报错 → C 包装错误路径 ptr 未初始化 → 解引用崩溃 | 补丁 0001：数组补 `#if defined(__RTMIDI_DUMMY__) RtMidi::RTMIDI_DUMMY #endif` |
| 2 | test_package 找不到 RtMidi.h | 上游把头文件装进 include/rtmidi/ 子目录 + 上游 cmake config 与 CMakeDeps 冲突 | includedirs 双根声明 + 删除上游 share/rtmidi 配置 |

## 依赖版本

- 无第三方 Conan 依赖（pthread 系统库）

## 验证结果（真机实测后回填）

- 上游: apinames（dummy 列出）+ testcapi 0 端口，2/2 退出码 0
- 消费者: **8/8 契约断言通过 + 1/1 鸿蒙特有完整消费者流程通过**（ctest 2/2 + 直接执行；流程真实链接 `rtmidi::rtmidi`，执行 API 发现、dummy 输入/输出会话、虚拟端口及 NoteOn/NoteOff 生命周期；dummy WARNING 如期出现）
- 包产物: include(RtMidi.h/rtmidi_c.h) + lib/librtmidi.a + cmake 配置

## 注意事项

- PR 前缀【知识库扩展】；任务分支 feat/rtmidi-6.0.0
