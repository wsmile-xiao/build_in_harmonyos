# rtmidi 6.0.0 知识证据报告

- 任务：rtmidi C++ 适配（知识库扩展，ohpcd contrib-2590）
- 真机：10.195.180.238，隔离 job `device-b/rtmidi-kb-20260920`
- 日期：2026-09-20；状态：执行中（【实测】= 真机原始输出）

## 0. 环境指纹

同 rcheevos job（clang 15.0.4 aarch64-unknown-linux-ohos、Conan 2.29.1、SDK cmake 3.28.2、profile sha 367f2b79…）。

## 1. 上游事实

- 无 MIDI 子系统的 OHOS 上，上游 CMake 探测 ALSA/JACK 全空且不报错（仅显式请求 Jack 才 FATAL_ERROR）
- 源码级自动回退：RtMidi.cpp:88-90 `#if !defined(__LINUX_ALSA__) && … #define __RTMIDI_DUMMY__`
- dummy 后端契约（RtMidi.cpp MidiInDummy/MidiOutDummy）：portCount=0、openPort/openVirtualPort/closePort/sendMessage 均 no-op、构造时发 WARNING "provides no functionality"；外层 RtMidiOut::openPort 为纯转发（RtMidi.h:667）
- 上游 tests/ 为示例程序集；apinames 含真实断言（API 名称映射 + 非法 API 返回 Unknown）

## 2. EVID 矩阵

### EVID-01 conan create（含上游 apinames+testcapi）
【实测】退出码 0；apinames 输出 `* 5 'dummy': 'Dummy'`（C++/C 双向映射均列出 dummy）；
testcapi 输出 `MIDI input ports found: 0 / MIDI output ports found: 0` 且退出 0。

### EVID-02 apinames 输出（dummy 编译证明）
【实测】修复前（未打补丁）：API 列表**为空**（dummy 未列出的上游缺陷实证）；
修复后：`* 5 'dummy': 'Dummy'`。

### EVID-03 消费者 dummy 契约断言（8 项）
【实测】直接执行输出 `test_rtmidi: OK (dummy-API fallback verified on OHOS)`；
与完整流程共同由 ctest 2/2 覆盖。
（含 dummy 构造 WARNING "MidiOutDummy: This class provides no functionality." 如期出现）。

### EVID-04 鸿蒙特有完整消费者流程（1 项）
【实测，2026-09-25】`rtmidi_dummy_workflow` 真实链接 `rtmidi::rtmidi`，依次执行
API 发现、dummy 输入/输出会话创建、虚拟端口生命周期、NoteOn/NoteOff 投递和关闭；
输出 `workflow: discovered dummy API` 和 `workflow: dummy MIDI session completed`，退出码 0。
ctest 2/2 通过（`test_rtmidi` + `rtmidi_dummy_workflow`）。该流程在无硬件的 dummy
后端不产生真实 MIDI I/O；成功证明完整消费者调用链可执行。

## 3. 测试统计
上游 apinames+testcapi 2/2；消费者 8/8 契约断言 + 1/1 鸿蒙特有完整消费者流程。

## 3.5 缺陷链实录（首跑）
未打补丁时：apinames 空 API 列表（exit 0，空列表无断言可失败）→ testcapi
`rtmidi_in_create_default()` 返回未初始化 ptr 的包装 → `rtmidi_get_port_count` 解引用
垃圾指针 → **SIGSEGV（Signal 11，exit 139）**。补丁 0001 后全链修复。

## 4. 影子 CI

- 修复提交 `52f286fa`：CI #60810 通过（Conan test_package、L0、L1 全通过）。
- 历史基线 #57892 已通过。
