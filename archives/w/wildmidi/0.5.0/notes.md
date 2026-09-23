# wildmidi 0.5.0 适配笔记

## 编译环境
- 构建系统: CMake (上游 CMakeLists.txt)
- 编译日期: 2026-09-13
- 编译器: clang 15 (OHOS SDK)
- 状态: built
- 平台: HarmonyOS PC aarch64 (os=OHOS, triplet aarch64-linux-ohos)

## 软件概况
WildMIDI 是一个简单的 MIDI 播放库（软波表合成器），支持 GUS patch set、
SoundFont2 (内嵌 TinySoundFont) 与内置 OPL3 FM 合成器 (Nuked-OPL3-fast +
内嵌 DMXOPL 音色库)。库为 LGPL-3.0+，命令行播放器为 GPLv3。

## 适配决策

### 只构建库 (WANT_PLAYER=OFF)
- 播放器依赖平台音频后端 (ALSA/OSS/SNDIO/CoreAudio/WinMM)，OHOS 均无
- WANT_ALSA/WANT_OSS 在非 Linux/BSD 系统默认 OFF 且依赖 WANT_PLAYER，
  显式传 OFF 以文档化意图
- 库本身纯 C + libm，无平台 API 依赖 → 零补丁适配

### 无外部依赖
- 内置 OPL3 合成器: WildMidi_Init("@opl3", 44100, 0) 即可初始化，无需
  GUS pat / SF2 / timidity 配置文件 (见上游 docs/OPL3.md)
- SF2 支持经内嵌 TinySoundFont (src/tsf/tsf.h)

### CMake 4.x 兼容
- 上游 cmake_minimum_required(VERSION 3.4...3.10) 低于 3.5，CMake 4.x 拒绝
- 命令行传 CMAKE_POLICY_VERSION_MINIMUM=3.5（不修改源码）

### 构建模式
- libdeflate/wavpack 模式: 自发现 ohos.toolchain.cmake + 裸 cmake，
  绕开 conan_toolchain 的 generator 路径问题
- make -j1 (OHOS 惯例)
- 共享库需重签 (binary-sign-tool, 同 libdeflate/wavpack)

## 编译步骤

```bash
cmake -B build-ohos -S . \
  -DCMAKE_TOOLCHAIN_FILE=<ohos.toolchain.cmake> \
  -DOHOS_ARCH=arm64-v8a \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DWANT_PLAYER=OFF -DWANT_ALSA=OFF -DWANT_OSS=OFF -DWANT_SNDIO=OFF \
  -DWANT_OPENAL=OFF -DWANT_DEVTEST=OFF \
  -DBUILD_SHARED_LIBS=ON -DWANT_SF2=ON \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DBUILD_TESTING=ON
cmake --build build-ohos -- -j1
ctest --test-dir build-ohos --output-on-failure   # 上游 test_tokenize
cmake --install build-ohos --prefix <pkg>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 拒绝配置 | 上游 cmake_minimum_required(3.4) < 3.5 | 命令行 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | 播放器音频后端缺失 | OHOS 无 ALSA/OSS/SNDIO | WANT_PLAYER=OFF 只建库 |
| 3 | 测试需要音色文件 | 传统路径需 GUS pat/SF2 | 使用内置 OPL3 合成器 ("@opl3") 零文件测试 |
| 4 | "Error running link command: no such file or directory"（造 .a 时） | OHOS SDK llvm/bin 只有 llvm-ar 无 llvm-ranlib，ohos.toolchain.cmake 把 CMAKE_RANLIB 指向它（知识库 E385，brotli/OpenCV/SuiteSparse 同坑） | 命令行 -DCMAKE_RANLIB=$(which llvm-ranlib)（hnp bin 有 llvm-ranlib 别名） |
| 5 | test_package 报 "too short (File corrupt)" | 自构造 MIDI 的 MTrk 长度字段写 20，实际载荷 19 字节 | 修正轨道长度字段为 19（41 字节总长） |

## 依赖
- 无外部编译依赖（仅 libm）
- test_package 使用 "@opl3" 配置，无需下载任何音色数据

## 产物
- lib/libWildMidi.so.2.2.0 (SONAME libWildMidi.so.2) + 符号链接
- include/wildmidi_lib.h
- lib/cmake/WildMidi/ (CMake config: WildMidi::libwildmidi)
- lib/pkgconfig/wildmidi.pc

## 测试

### 上游官方测试 (L1, ctest)
- test/test_tokenize.c → test_tokenize: WM_LC_Tokenize_Line 配置行解析
  单元测试（带引号路径、空引号、未闭合引号、注释剥离等 assert 断言）
- 链接 libwildmidi-static，在 conanfile.py build() 内 ctest 原生运行于 OHOS

### test_package (消费者视角)
- test_wildmidi.c: GetString → GetVersion(0x000500) → Init("@opl3") →
  MasterVolume → OpenBuffer(内存构造 MIDI) → GetInfo → GetOutput(PCM 合成) →
  Close/Shutdown 全生命周期，10 项断言

## 验证结果

```
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing  → exit 0
Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created
上游测试 (build() 内 ctest): 1/1 tokenize Passed (100%)
test_package: ALL CHECKS PASSED (10 断言: GetString/GetVersion/Init(@opl3)/
  MasterVolume/OpenBuffer/GetInfo/GetOutput/Close/Shutdown)
签名: binary-sign-tool self-sign libWildMidi.so.2.2.0 ✅
```

日志留存: ~/wt-wildmidi-conan-create.log

## 注意事项
- 版本号注意: 项目版本 0.5.0, 但 .so SONAME 版本是 2 (SOVERSION=2, VERSION=2.2.0)
- SPDX 许可证: 库 LGPL-3.0-or-later (播放器 GPLv3 未构建)

## 软件级信息（并入说明）
按仓库 PF9 路径闸惯例，软件级 README/manifest（archives/w/wildmidi/ 直下 4 层路径）
不再随 PR 提交，相关内容并入本 notes.md：

### 软件级元数据（原 manifest.yaml 摘要）
- display: WildMIDI
- category: library
- license: LGPL-3.0-or-later
- versions: 0.5.0 (built, 2026-09-13)

### 软件描述（原 README.md 摘要）
简单、轻量的 MIDI 播放库（软波表合成器）。支持 GUS patch set、SoundFont2
（内嵌 TinySoundFont）以及内置 OPL3 FM 合成器（Nuked-OPL3-fast + 内嵌
DMXOPL 音色库，无需任何外部音色文件）。无外部编译依赖（仅 libm）。

```c
/* 内置 OPL3 合成器初始化，无需音色文件 */
WildMidi_Init("@opl3", 44100, 0);
```
