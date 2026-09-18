# wildmidi 0.4.5 适配笔记（GLM-25，2026-09-14）

## 任务信息
- 平台任务号 13414，活动=开源鸿蒙PC专项积分赛-依赖
- 分支 feat/wildmidi-0.4.5，worktree ~/qzy/GLM-25-wildmidi-0.4.5
- 上游 https://github.com/Mindwerks/wildmidi tag wildmidi-0.4.5
  tarball https://codeload.github.com/Mindwerks/wildmidi/tar.gz/refs/tags/wildmidi-0.4.5
  sha256=116c0f31d349eaa74a630ed5a9a17b6a351204877a4ed9fb9aacd9dbd7f6c874

## 适配决策
1. OHOS 无 ALSA/OSS/OpenAL 音频后端，按上游 CMake 开关切纯库模式：
   WANT_PLAYER=OFF、WANT_PLAYERSTATIC=OFF、WANT_DEVTEST=OFF，
   保留 libWildMidi 全部公开 API；上游 player 与 DevTest 在无后端平台本就不可用。
2. 上游声明 cmake_minimum_required(3.1)，设备 CMake 4.1.2 直接拒绝；
   在 cmake.configure(variables=...) 以命令行 -D 传 CMAKE_POLICY_VERSION_MINIMUM=3.5
   （知识 E103；注意 toolchain 文件内的 set() 时机太晚，必须命令行 -D）。
3. shared=False 时同时 -DWANT_STATIC=ON 产出静态库。
4. 包内产物名为上游真实命名 libWildMidi.so/libWildMidi.a（LIBRARY_DYN_NAME/
   LIBRARY_STATIC_NAME，大写 WM），package_info 按实际产物声明 libs=["WildMidi"]。
5. conandata URL 使用 codeload.github.com 官方 tag 端点（与 /archive/ URL 同一字节流、
   同 sha256）：codeload 直连稳定，且不含 "https://github.com" 子串，
   避免 conan-verify 的 E017 ghfast 镜像注入（今晚 ghfast.top 全程超时）。
   codeload URL 无 .tar.gz 后缀，get() 显式 filename= 防误判 ZIP。
6. 消费者测试 test_wildmidi.c：编译链接 libWildMidi，断言公开 API 行为
   （版本宏、Init 缺失配置失败、GetError 非空、未初始化 Shutdown 返回 -1、
   ClearError 清态）。注意上游 0.4.5 公开 API 拼写为 WildMidi_*（小写 i）。

## 上游测试账本（四维）
- N_static = 0：上游 0.4.5 无自动化测试。CMake 无任何测试目标（无 add_test、
  无 enable_testing/CTest）；test/test.c 为手动播放示例（依赖手工 wildmidi.cfg
  与 MIDI 资产、无断言）；src/DevTest.c 属 WANT_DEVTEST 开发工具非测试。
- N_consumer = 1（test_package/test_wildmidi.c，5 组断言），真机运行 5/5 通过。
- R40 标注：实际 MIDI 合成路径（WildMidi_GetOutput 等）依赖 GUS patch 音色库
  （wildmidi.cfg + 数十 MB patch 资产），上游亦不提供此类自动化测试资产，
  本包消费者测试未覆盖合成路径，需人工确认适配完整性（AI 检视 P3 已确认此口径）。

## 知识调用与路径 B 判断
- 调用知识：E103（CMake 4 移除 <3.5 兼容：cmake_minimum_required 需
  CMAKE_POLICY_VERSION_MINIMUM）、cmake 检查清单。
- 查重：CMake 4 兼容坑已由 E103（bump-cmake-minimum-version）覆盖；
  音频后端禁用为单库平台决策；无新增可跨库复用知识 → **不走路径 B**。
---

**编译结束**: 2026-09-14 21:32
**最终状态**: built
