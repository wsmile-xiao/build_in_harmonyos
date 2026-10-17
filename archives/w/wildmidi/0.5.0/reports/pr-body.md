- **三方库名称**：wildmidi
- **上游版本**：0.5.0 (tag wildmidi-0.5.0)
- **上游仓库地址**：https://github.com/Mindwerks/wildmidi
- **适配路径**：路径 A（基础适配，无补丁）
- **使用知识库**：E385（OHOS SDK 缺 llvm-ranlib，CMAKE_RANLIB 覆盖）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1 | test/test_tokenize.c（WM_LC_Tokenize_Line 配置行解析，assert 断言） |
| 集成测试 | 0 | 上游无集成测试目录 |
| 其他测试 | 0 | - |
| **合计** | **1** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | 不变 | test_tokenize 经 BUILD_TESTING=ON 在 build() 内 ctest 原生运行 |
| 集成测试 | 1 | +1 | test_package 全 API 生命周期（消费者视角，非上游用例） |
| 鸿蒙特有测试 | 0 | - | 平台无特有差异，无需新增 |
| **合计** | **2** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：test_package/consumer 视角公开 API 全生命周期测试（10 项断言）
> - **补全原因**：上游 test/ 仅覆盖内部函数 WM_LC_Tokenize_Line，无消费者视角的库初始化→打开→合成→关闭链路测试；上游 test/test.c 需要真实音色文件且未注册进 ctest
> - **新增测试文件清单**：
>   1. `archives/w/wildmidi/0.5.0/test_package/test_wildmidi.c` — 使用内置 OPL3 合成器（"@opl3" 配置，零音色文件依赖）：GetString → GetVersion(0x000500) → Init → MasterVolume → OpenBuffer(内存构造 MIDI) → GetInfo → GetOutput(PCM 合成) → Close/Shutdown

## 验证结果

- 编译状态：**通过**（conan create 全绿，Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created）
- 上游测试用例通过率：**1/1（100%）**
- 新增测试用例通过率：**1/1（100%）**

### 编译验证

```
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing → exit 0
[100%] Built target test_tokenize
100% tests passed, 0 tests failed out of 1
[ 47%] Linking C shared library libWildMidi.so
[100%] Built target libwildmidi
binary-sign-tool sign libWildMidi.so.2.2.0 -selfSign 1 → OK
Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created
```

### 产物

| 产物 | 说明 |
|------|------|
| lib/libWildMidi.so.2.2.0 (SONAME libWildMidi.so.2) | 共享库（已自签） |
| include/wildmidi_lib.h | 公开头文件 |
| lib/cmake/WildMidi/*.cmake | CMake 配置（WildMidi::libwildmidi） |
| lib/pkgconfig/wildmidi.pc | pkg-config |

### 适配要点

- CMake 构建（libdeflate 模式：自发现 ohos.toolchain.cmake + 裸 cmake），make -j1
- **WANT_PLAYER=OFF**：命令行播放器依赖 ALSA/OSS/SNDIO/CoreAudio 音频后端，OHOS 均无 → 只构建库；WANT_ALSA/WANT_OSS/WANT_SNDIO/WANT_OPENAL 显式 OFF
- **无强制外部依赖**：内置 OPL3 FM 合成器（Nuked-OPL3-fast + 内嵌 DMXOPL 音色库）无需 GUS pat/SF2 文件；SF2 支持经内嵌 TinySoundFont
- **CMAKE_POLICY_VERSION_MINIMUM=3.5**：上游 cmake_minimum_required(3.4...3.10) 被 CMake 4.x 拒绝
- **-DCMAKE_RANLIB 覆盖**（知识库 E385）：OHOS SDK llvm/bin 只有 llvm-ar 无 llvm-ranlib，静态库打包需用 hnp bin 的 llvm-ranlib
- 零补丁（patches: {}），库纯 C + libm，无平台 API 依赖
- 库为 LGPL-3.0-or-later（播放器 GPLv3 未构建）

### test_package 运行结果

```
RUN: ./test_wildmidi
OK: version string = WildMidi Processing Library 0.5.0
OK: numeric version = 0x000500
OK: WildMidi_Init with built-in OPL3 bank
OK: WildMidi_OpenBuffer
OK: info: total_midi_time=500 ms, approx_total_samples=22050
OK: WildMidi_GetOutput produced 16384 bytes of PCM
ALL CHECKS PASSED
```

## 补充说明

- 平台任务：contrib-7361
- .so SONAME 为 libWildMidi.so.2（SOVERSION 2, VERSION 2.2.0），与项目版本 0.5.0 不同属上游惯例，无碍
- commands.json：本包仅构建库（WANT_PLAYER=OFF / WANT_DEVTEST=OFF，无 bin/ 产物），按 R38 判定不需要
- 已知限制：播放器未构建（OHOS 无音频后端）；GUS/SF2 音色文件需使用者自行提供，内置 OPL3 可零文件使用
