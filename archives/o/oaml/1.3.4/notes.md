# oaml 1.3.4 适配笔记（HarmonyOS PC / aarch64）

## 编译环境

- 构建系统：**CMake**（cmake_minimum_required(VERSION 2.8)，CMake 4 需
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 放行）
- 编译日期：2026-10-08
- 编译器：OHOS NDK clang（sysroot 26.0.0.18，musl libc，aarch64-linux-ohos）
- Conan：2.29.1
- 状态：built

## 源码与上游测试入口核验（R51）

| 项 | 结论 |
|---|---|
| 上游仓库 | <https://github.com/oamldev/oaml>（tag `v1.3.4`） |
| sha256 | `4000dabf043938bcff3069ead1052fb06a77a7004bda67adcc5bc9538d32908f`（与 AUR/FreshPorts 公布值一致） |
| 顶层结构 | `CMakeLists.txt cmake/ include/ src/ vs/`（63 文件） |
| `tests/` 目录 | **不存在** |
| ctest / pytest 注册 | **不存在** |
| 唯一测试入口 | **`ENABLE_TEST` CMake 开关 → `oamlTest` 可执行文件**（`src/test.cpp`，默认 OFF） |

`oamlTest` 性质：交互式 demo —— `InitAudioDevice(44100)` 依赖 RtAudio 真实输出设备
（OHOS 无 ALSA/Pulse/JACK 后端），随后从 stdin 逐字符读命令直到输入 `q`，
**无任何自动化断言**。

结论（R51 三步法如实申报）：上游自动化测试用例数 = **0**；无头环境不可运行交互
demo。按规范：①`build()` 中以 `-DENABLE_TEST=ON` 真实编译该入口（证明上游测试
入口在 OHOS 工具链下可编译，构建日志留证）；②新增 1 个鸿蒙消费者用例
`test_package/test_oaml.cpp`（9 条断言，真实调用 oaml C++ API：Init(defs) →
PlayTrack → MixToBuffer 真实解码混音 → 播放状态断言 → StopPlaying → Shutdown），
在 OHOS PC 上真实运行。

## 依赖（W0 预检）

| 依赖 | 版本 | 制品仓验证（R35/R36） |
|---|---|---|
| libvorbis | 1.3.7 | `conan download libvorbis/1.3.7 -r=ohpcd --only-recipe` → rc=0（revision 8d85ac0a） |
| libogg（libvorbis 传递依赖） | 1.3.5 | `conan download libogg/1.3.5 -r=ohpcd --only-recipe` → rc=0（revision acc8d10e） |
| libsoxr | 0.1.3 | `conan download libsoxr/0.1.3 -r=ohpcd --only-recipe` → rc=0（revision 019c7372） |

R36：三依赖均已发布到制品仓，无阻塞，未使用本地缓存或 `--build=missing` 绕过。

### 平台适配点（OHOS）

1. **CMake 4 兼容**：`cmake_minimum_required(VERSION 2.8)` 被 CMake 4 硬拒绝
   （FreeBSD 侧同记录 "does not build with CMake 4"）→
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`，免打源码补丁。
2. **RtAudio 关闭**：OHOS 无 ALSA/PulseAudio/JACK；`ENABLE_RTAUDIO=OFF`。
   oamlBase.cpp 对 `__HAVE_RTAUDIO` 有完整守卫（InitAudioDevice 返回 OAML_ERROR），
   混音核心（MixToBuffer/解码/条件切换）不受影响。
3. **Unity 插件关闭**：`ENABLE_UNITYPLUGIN=OFF`（Unity 引擎专用 MODULE 库，与 OHOS 无关）。
4. **依赖接线**：上游 Find 模块用裸 `find_path/find_library`，交叉链
   FIND_ROOT_PATH=ONLY 下搜不到 conan 依赖 → 预置
   `VORBIS_INCLUDE_DIR/OGG_LIBRARY/VORBISFILE_LIBRARIES/SOXR_LIBRARIES` 等缓存变量
   指向依赖包真实路径。
5. **代码签名**：包内 `liboaml.so*` 与 test_package 消费者二进制均用
   binary-sign-tool 自签（鸿蒙 PC XPM 要求，ML-0043）。
6. **Ninja 生成器**：本沙箱 HMDFS 不支持 FIFO，Unix Makefiles 的 jobserver（mkfifo）
   报 Operation not permitted 且偶发 spawn 失败 → `-G Ninja`（CI 能力矩阵 ninja ✅）。

无源码补丁（patches_applied: []），所有适配均在 conanfile.py 的 CMake 开关层完成。

## 验证结果

见 `reports/test-report.md`（上游测试统计 + 鸿蒙消费者用例逐项断言）、
`reports/conan-verify-report.md`（conan create/conan-verify 复验）。

## 调试实录（ROOT-CAUSE → FIX → VERIFICATION）

构建期间经历 6 轮 `conan create`，全部真实执行、逐轮闭环：

| # | 首个错误 | 根因 | 修复 | 复验 |
|---|---|---|---|---|
| 1 | `oamlAudioFile.h:27: fatal error: 'soxr.h' file not found` | 上游错配：FindSoxr.cmake 只定义复数 `SOXR_INCLUDE_DIRS`，CMakeLists.txt:126 用单数 `${SOXR_INCLUDE_DIR}` → soxr include 从未加入编译 | 配方预置单复数两个缓存变量 | soxr.h 可找到 |
| 2 | `vorbis/codec.h:25: fatal error: 'ogg/ogg.h' file not found` | 上游 CMakeLists:113 只加 VORBIS/VORBISFILE include，不加 OGG_INCLUDE_DIR，而 vorbis 头包含 ogg 头 | 配方用 CMAKE_C/CXX_FLAGS 补 `-I<ogg include>` | ogg.h 可找到 |
| 3 | `Error running link command: no such file or directory`（liboaml.a 归档，Makefile 生成器） | **OHOS SDK llvm/bin 缺 `llvm-ranlib`**（ohos.toolchain.cmake:338 硬指过去；llvm-ar 存在但 ranlib 不存在） | `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`（llvm-ranlib 与目标架构无关） | 静态库归档成功 |
| 4 | GitHub 源码下载超时（source()） | 网络瞬断（R41 外部因素） | 重试 | 下载成功 |
| 5 | `test_oaml.cpp:91: use of undeclared identifier 'oamlGetVersion'` | oaml.h 的 C API 段在 `#ifndef __cplusplus` 内，C++ 消费者须用 `oamlApi::GetVersion()` 成员 | 用例改用 C++ API | 编译通过 |
| 6 | 消费者用例 `MixToBuffer produces real decoded audio (non-silence)` 失败（其余 10 断言过） | 见下方专节 | 用例先 `SetAudioFormat` 再 `PlayTrack` | 11/11 通过 |

### 消费者用例静音问题定位（插桩实录）

用 62 处 fprintf 插桩上游源码 + 完整源码编译探针逐层定位：

1. `LoadTrack=-1`：`oamlAudioFile::Load()` 失败 —— `wavFile::Read` 在数据块读完后的下一次调用
   走 ReadChunk → 在 EOF 读块头失败 → 关 fd 并返回 -1（clean EOF 被当致命错误）。
   **这是上游缺陷**，但只影响预加载 API（LoadTrack/LoadTrackProgress），不影响流式混音
   路径（数据已在 buffer 中，Read32 正常返回），消费者规避方式为不依赖预加载返回值。
2. `MixToBuffer` 恒静音：`HasFinished samplesCount=1 samplesToEnd=0 totalSamples=0` ——
   OpenFile 的 `#ifdef __HAVE_SOXR` 重采样分支在 `base->GetSampleRate()==0`（未调
   SetAudioFormat）时计算 `totalSamples = 88200 × 0 / 44100 = 0`、`samplesPerSec=0`
   → HasFinished() 恒真 → 每帧 PlayNext 重开文件重置 samplesCount → 永远只读第 0
   采样（正弦起点=0）→ 恒静音。
3. **根因是消费者调用顺序**：上游 oamlTest 先 `InitAudioDevice(44100)`（内含
   SetAudioFormat）再 PlayTrack。用例改为先 `SetAudioFormat(44100,1,2,false)` 再
   PlayTrack → 11/11 断言通过。

另：`MixToBuffer(buffer, size)` 的 size 语义 = **采样点数**（frames×channels，与
RtAudio 回调 `nBufferFrames*2` 一致），不是字节数。

## 复现方式

```bash
conan create archives/o/oaml/1.3.4 -pr:h=ohos-aarch64-local -pr:b=ohos-aarch64-local
# test_package 在 conan create 内自动编译并运行 test_oaml（本机 OHOS PC 真实执行）
```
### 对话 #1 [2026-10-08] soxr/vorbis 头文件探测失败与 CMake 4 兼容

- 问题: 首次 `conan create` 报 `aif.cpp → oamlAudioFile.h:27: fatal error: 'soxr.h' file not found`；
  修复后进一步报 `vorbis/codec.h` 找不到 `<ogg/ogg.h>`
- 操作: 上游 FindSoxr.cmake 只定义复数 `SOXR_INCLUDE_DIRS` 而 CMakeLists 用单数
  `${SOXR_INCLUDE_DIR}`（单复数错配），且 CMakeLists 未把 OGG include 加进编译——
  均在配方层预置 find 缓存变量（单复数都给）+ CFLAGS 补 `-I<ogg include>`，
  免源码补丁；CMake 4 对 `cmake_minimum_required(VERSION 2.8)` 的硬拒绝用
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 放行
- 结果: 头文件全部解析成功，编译推进到归档阶段

### 对话 #2 [2026-10-08] llvm-ranlib 缺失与 HMDFS FIFO jobserver

- 问题: `liboaml.so` 链接成功但静态库归档报 `Error running link command`/
  `llvm-ranlib: inaccessible or not found`；改 Unix Makefiles 生成器又遇
  `make: jobserver mkfifo: Operation not permitted`
- 操作: OHOS SDK llvm/bin 无 llvm-ranlib 而 ohos.toolchain.cmake 硬指过去 →
  配方显式 `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`（归档工具与目标
  架构无关）；HMDFS 不支持 FIFO → 生成器改 `-G Ninja` 规避 jobserver
- 结果: 静态库与共享库全部构建成功，包安装与二进制签名正常

### 对话 #3 [2026-10-08] 消费者用例恒静音的根因定位

- 问题: test_oaml 运行 11 断言中 `MixToBuffer` 恒静音、playing info 显示 pos=0
- 操作: 插桩 wav/audioFile/Track/Audio 四层逐步收敛——文件完整读入
  （bufsize=176400）但 `Audio::Open after` 显示 file_sps=0/totalSamples=0；
  根因是消费者未先 `SetAudioFormat` 就 `PlayTrack`，OpenFile 的 soxr 重采样分支
  按 GetSampleRate()==0 计算 `totalSamples=88200×0/44100=0` → HasFinished 恒真
  → 每帧 PlayNext 重开文件、恒静音；用例调整为先 SetAudioFormat(44100,1,2,false)
- 结果: 11/11 断言全部通过（含新增鸿蒙消费者用例：真实解码混音出非零采样）
---

**编译结束**: 2026-10-09 00:02
**最终状态**: built
