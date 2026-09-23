# wildmidi 0.4.6 适配笔记

## 任务信息
- 平台任务号 11900，活动=开源鸿蒙PC专项积分赛
- 分支 feat/wildmidi-0.4.6
- 上游 https://github.com/Mindwerks/wildmidi tag wildmidi-0.4.6
  tarball https://codeload.github.com/Mindwerks/wildmidi/tar.gz/refs/tags/wildmidi-0.4.6
  sha256=051b8c51699af594ddd3e4e3b06bad3564e9499c3c6b9e6f880cb2f92bcfa9c8
- 范本：同系列 archives/w/wildmidi/0.4.5（已在 main）

## 适配决策
1. OHOS 无 ALSA/OSS/SNDIO/OpenAL 音频后端，按上游 CMake 开关切纯库模式：
   WANT_PLAYER=OFF、WANT_PLAYERSTATIC=OFF、WANT_DEVTEST=OFF，
   WANT_ALSA/WANT_OSS/WANT_SNDIO/WANT_OPENAL 一并显式置 OFF（它们只被 player 目标使用）。
   0.4.6 相对 0.4.5 重构了音频后端探测（player 移到 src/player 子目录、
   ALSA/OSS/SNDIO 改为 CMAKE_DEPENDENT_OPTION 且默认值按 CMAKE_SYSTEM_NAME 判定）；
   OHOS 的 CMAKE_SYSTEM_NAME=OHOS 不匹配 ".*Linux"，ALSA/OSS 默认本就是 OFF，
   显式再关一次是为了不依赖默认值。
2. 上游声明 cmake_minimum_required(3.4...3.5)，设备 CMake 4.x 拒绝 <3.5 的下限；
   在 cmake.configure(variables=...) 以命令行 -D 传 CMAKE_POLICY_VERSION_MINIMUM=3.5
   （知识 E103；toolchain 文件内的 set() 时机太晚，必须命令行 -D）。
3. shared=False 时同时 -DWANT_STATIC=ON 产出静态库（上游在
   "NOT BUILD_SHARED_LIBS AND NOT WANT_STATIC" 时直接 FATAL_ERROR）。
4. 包内产物名为上游真实命名 libWildMidi.so / libWildMidi.a
   （src/CMakeLists.txt 的 LIBRARY_DYN_NAME / LIBRARY_STATIC_NAME，
   非 MSVC 时均为 "WildMidi"），package_info 按实际产物声明 libs=["WildMidi"]。
5. conandata URL 使用 codeload.github.com 官方 tag 端点（与 /archive/ URL 同一字节流、
   同 sha256），避免第三方镜像（PF7）；codeload URL 无 .tar.gz 后缀，
   get() 显式 filename= 防误判 ZIP。
6. 消费者测试 test_wildmidi.c：编译链接 libWildMidi，6 组断言
   （版本宏、WildMidi_GetVersion、WildMidi_GetString(WM_GS_VERSION)+未知 tag 返回 NULL、
   Init 缺配置失败、GetError/ClearError、未初始化 Shutdown 置 WM_ERR_NOT_INIT）。
   注意上游公开 API 拼写为 WildMidi_*（小写 i）。

## 上游测试账本（四维）
- N_static = 0：上游 0.4.6 无自动化测试。
  取数：`grep -rn "enable_testing\|add_test\|include(CTest)" . --include=CMakeLists.txt`
  → 0 命中；`ls test/` 只有 test.c（手工播放示例，需自备 wildmidi.cfg 与 MIDI 资产、无断言）；
  src/DevTest.c 属 WANT_DEVTEST 开发工具，非测试。
- N_consumer = 6 组断言（test_package/test_wildmidi.c），真机运行通过。
- R40 标注：实际 MIDI 合成路径（WildMidi_GetOutput 等）依赖 GUS patch 音色库
  （wildmidi.cfg + 数十 MB patch 资产），上游亦不提供此类自动化测试资产；
  0.4.6 无 0.5.0 那样的内置 OPL3/SF2 合成器，故消费者测试未覆盖合成路径，
  与 0.4.5 同口径（AI 检视曾确认此口径）。

## 知识调用与路径 B 判断
- 调用知识：E103（CMake 4 移除 <3.5 兼容：cmake_minimum_required 需
  CMAKE_POLICY_VERSION_MINIMUM）。
- 查重：CMake 4 兼容坑已由 E103 覆盖；音频后端禁用为单库平台决策；
  0.4.6 相对 0.4.5 的 CMake 重构不产生可跨库复用的新坑 → **不走路径 B**。

---

**编译结束**: 2026-09-19
**最终状态**: built
