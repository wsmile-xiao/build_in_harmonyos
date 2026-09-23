# cubicsdr 0.2.7 适配笔记（HarmonyOS PC）

## 编译环境
- 构建系统: 上游 CMake（老式 2.8 版 CMakeLists）→ 核心层独立生成 CMake 工程编译
- 编译器: clang/clang++ 15.0.4（llvm aarch64-linux-ohos）
- Profile: ohos-aarch64（os=OHOS 6.0 / arch=armv8 / libc++ / C++17 / Release）
- 状态: built（本机 conan create 全绿 + test_package 11/11 ALL PASS）

## 上游信息
- 上游: https://github.com/cjcliffe/CubicSDR tag 0.2.7（ba7a35c336f8a8e0af8154b3075e5a3ac2b87c70）
- 源码 SHA-256: 790f851e08f1068081a8593dfd4a149c7414e7d70c1f5cafd287331df493b811
- 形态: SDR 收音机 GUI 大件（wxWidgets GUI + liquid-dsp DSP + SoapySDR 硬件抽象 + OpenGL 频谱/瀑布显示）

## 交付范围（C 类攻坚：分层核心库切割）

**上游完整 GUI 构建在 OHOS PC 不可行**（穷尽验证）：
1. `find_package(OpenGL REQUIRED)` 需 GLX——OHOS 只有 EGL/GLES（`nm -D` 实测系统 libGLESv3.so 与 SDK libGLv4.so 均无 glBegin/glOrtho 立即模式符号；CMake 探针报 `missing: OPENGL_opengl_LIBRARY OPENGL_glx_LIBRARY`）
2. `find_package(wxWidgets COMPONENTS gl core propgrid adv base)` 需 wxCore GUI——制品仓 wxwidgets/3.3.3 为 wxBase 非 GUI 变体（wxUSE_GUI=OFF，_LIBS_RELEASE 仅 wx_baseu-3.3 系）
3. 音频：OHOS 无 PulseAudio/ALSA/JACK/OSS（上游 Linux 段默认 USE_AUDIO_PULSE=ON 不可满足）

**交付 libcubicsdr-core.a**（上游源文件 verbatim 编译 + 1 个上游缺陷修复补丁）：
- Modem 引擎：基类 3 + analog 10 制式（AM/FM/FMS/NBFM/USB/LSB/DSB/CW/IQ）+ digital 13 制式（APSK/ASK/BPSK/DPSK/FSK/GMSK/OOK/PSK/QAM/QPSK/SQAM/ST）
- 线程框架：IOThread / ThreadBlockingQueue / Timer
- 序列化：DataTree + vendored tinyxml
- vendored RtAudio（dummy 后端——RtAudio.h:629 无音频 API 宏时上游自动回退）

超出切割面（如实申报）：GUI 前端（AppFrame/visual/forms/panel/ui）、demod 编排层与 SDR 设备线程（src/demod + src/sdr，60+ 处 wxGetApp() GUI 回调耦合）、AudioThread 设备管理类（wxGetApp 耦合 + GUI-only）。详见 reports/upstream-tests.md。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMakeLists 在 OHOS configure 即败 | find_package(OpenGL REQUIRED) 需 GLX；find_package(wxWidgets) 需 wxCore GUI | 不走上游主 CMakeLists；生成独立核心层 CMake 工程（core-build/），35 个上游编译单元 verbatim 编译 |
| 2 | ENABLE_DIGITAL_LAB=0 时 ModemFSK/ModemGMSK 编译失败 | 上游缺陷：outStream 成员仅 LAB=1 声明，两文件无条件引用（travis 恒 LAB=1 掩盖） | patches/0001：#if ENABLE_DIGITAL_LAB 守卫 outStream 引用，保留解调状态机调用（fskdem/gmskdem_demodulate 不受影响） |
| 3 | 数字 Modem 构造/析构 100% Signal 11（进程退出阶段） | OHOS clang-15 工具链 libc++ 弱符号双副本：.a 内联 weak 析构 vs libc++_shared.so 副本 → ios_base::~ios_base invalid free（ASan 定位，8/8 复现） | 库编译改 ENABLE_DIGITAL_LAB=0——stringstream 成员彻底出库（其唯一消费者是 wx GUI DigitalConsole，本平台超范围）；analog/digital 全部构造析构干净 |
| 4 | makeModem("FM") 返回 nullptr | 上游设计：工厂注册在 GUI 主程序 CubicSDR.cpp initModemList()（应用层职责） | test_package 按上游同款方式注册后查询（21 种全通过） |
| 5 | test 二进制运行报 libc++_shared.so 找不到 / mksh 不能执行 ELF | OHOS 加载器路径 + /system/bin/sh 限制 | test() 用 bash 包装 + LD_LIBRARY_PATH=/system/lib64 前置（系统 libc++ 提供 __n1 符号；profile 既定方案） |
| 6 | CMakeToolchain 与生成工程的 conan 依赖装配 | build_script_folder 切换 configure 目录后 CMakeDeps 文件未注入 | conanfile 加 generators = "CMakeDeps"；test_package requirements 补 liquid-dsp（公共头依赖） |
| 7 | 头文件安装扁平化丢失子目录结构 | install(FILES GLOB) 不保留路径 | 改 file(COPY ... FILES_MATCHING) 镜像安装 src/ 树（排除 GUI 子树） |

## 源码修改
- 仅 patches/0001-guard-outstream-under-digital-lab.patch（上游 LAB=0 构建缺陷修复；见 conandata.yml 声明）
- 其余 35 个编译单元全部 verbatim（零源文件修改）

## 依赖版本（W0 已核 + R35 二进制实测可装）
- liquid-dsp/1.8.2（ohpcd 制品仓 done）
- soapysdr/0.8.1（ohpcd 制品仓 done；test_package 无硬件枚举定性用）
- wxwidgets/3.3.3（制品仓 done 但为 wxBase 非 GUI 变体——本包核心切割不依赖，GUI 层如实申报不可构建）

## 验证结果（2026-09-20，本机）

```
conan create . --build=missing -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
→ cubicsdr/0.2.7 package built (7e2545833da6cfd197a80426aba491ee066cc66b)

test_package（OHOS PC aarch64 实测运行）:
PASS: factory registry holds all 21 upstream-registered modes
PASS: makeModem instantiates every registered mode (21/21)
PASS: freqmod_create
PASS: FM demodulated audio produced (>0.2 s of samples)
  FM: tone amp=0.40006 ref amp=0.00049 (ratio 816.0)
PASS: FM audio carries the injected 1 kHz tone
PASS: AM demodulated audio produced
  AM: tone amp=0.00070 ref amp=0.00000 (ratio 206.4)
PASS: AM audio follows the injected 800 Hz envelope tone
PASS: USB demodulated audio produced
  USB: tone amp=0.31174 ref amp=0.00010 (ratio 3179.0)
PASS: USB audio carries the upper-sideband tone
PASS: modemcf_create(BPSK)
PASS: BPSK digital demodulate() chain runs to completion
PASS: no-hardware enumeration returns empty list (expected form on OHOS PC without SDR hardware)
→ cubicsdr 0.2.7 test_package: ALL PASS
```

DSP 闭环测试设计：liquid-dsp 调制器（业界标准）合成 FM/AM/USB/BPSK 信号 → CubicSDR 自身 Modem 引擎（被测物）demodulate() → Goertzel 独立音调检测（非 liquid FFT）——避免被测库自证。

---

**编译结束**: 2026-09-20
**最终状态**: built（待 CI 验证）
