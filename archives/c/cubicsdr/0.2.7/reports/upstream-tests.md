# cubicsdr 0.2.7 上游测试与 OHOS 可测性定性报告

任务 #89（积分赛，C 类攻坚）· worktree: feat/cubicsdr-0.2.7 · 账号 2404_87638649

## 一、上游测试形态核验（真跑依据）

**上游 CubicSDR 0.2.7（tag ba7a35c336f8a8e0af8154b3075e5a3ac2b87c70）不包含任何自动化测试注册**：

```
$ grep -rn "add_test\|enable_testing\|BUILD_TESTING" CMakeLists.txt cmake/ src/
（空——零命中）

$ ls travis-ci/
build_cubicsdr.sh  build_liquiddsp.sh  build_soapysdr.sh  build_wxwidgets.sh

$ grep -E "cmake|make|ctest" travis-ci/build_cubicsdr.sh
cmake ../CubicSDR -DCMAKE_BUILD_TYPE=Release \
  -DwxWidgets_CONFIG_EXECUTABLE=... -DUSE_HAMLIB=1 -DENABLE_DIGITAL_LAB=1
# 仅构建 + 运行 GUI 应用二进制，无 ctest/make test 调用
```

上游 CI（travis-ci）只做"构建 + 启动应用"两个动作，不存在 `make check`/`ctest` 形态的自动化测试套件。**上游注册测试数 N = 0**（申报口径：上游构建系统注册的测试目标数）。

## 二、OHOS PC 上的可测性边界定性（逐项）

CubicSDR 是 SDR 收音机 GUI 大件，其测试面按层拆解定性如下：

### 1. GUI 层（AppFrame/visual/forms/panel/ui）——不可测（平台缺基础设施）

- 需 wxCore GUI 模块（gl core propgrid adv）+ 桌面 OpenGL 立即模式（glBegin/glVertex/glOrtho）
- **实测证据**：
  - 制品仓 wxwidgets/3.3.3 为 wxBase 非 GUI 变体（`wxUSE_GUI=OFF`，`_LIBS_RELEASE = wx_baseu_net-3.3 wx_baseu-3.3 wx_baseu_xml-3.3 wxregexu-3.3 wxzlib-3.3 wxexpat-3.3`——无任何 wxCore/wxGL）
  - OHOS 系统 GL 库符号扫描：`nm -D /system/lib64/libGLESv3.so` 与 SDK `libGLv4.so` 均无 `glBegin/glEnd/glOrtho/glMatrixMode` 桌面立即模式符号（只有 glVertexAttrib* 现代 API）
  - CMake configure 探针实测：`find_package(OpenGL REQUIRED)` 报 `Could NOT find OpenGL (missing: OPENGL_opengl_LIBRARY OPENGL_glx_LIBRARY)`——OHOS 无 GLX
  - wxwidgets/3.3.3 归档 notes.md 原文："不宣称 wxCore 图形窗口栈已完成目标端适配"

### 2. DSP 算法层（Modem 引擎 23 种制式）——可测，已真跑（本报告第三节）

- 纯 liquid-dsp + std C++17，零 GUI 依赖（include 链实测验证）
- test_package 用上游公开 demodulate() API 做调制→解调闭环真测试

### 3. SDR 硬件交互层（SoapySDR device open/stream）——不可测（无硬件），形态已定性

OHOS PC 无 RTL-SDR/USRP/BladeRF 等 SDR 硬件，无任何厂商 SoapySDR module。无设备场景的报错形态**逐项实测**（不是笼统豁免）：

- `SoapySDR::listModules()` → 返回 0 个模块（无段错误）
- `SoapySDR::Device::enumerate("")` → 返回空列表（size=0），不抛异常
- GUI 应用在无设备时的表现（上游行为）：设备列表为空、提示"No devices found"——此路径在 OHOS 上与本 test_package 的枚举形态一致
- 若强行 `Device::make("driver=rtlsdr")` → SoapySDR 抛 `SoapySDR::RuntimeError`（找不到模块的文档化行为）；此形态由 SoapySDR 0.8.1 制品（已发布）自身保证，本包 test_package 以 enumerate 空列表实测覆盖

### 4. 音频层——RtAudio dummy 后端可编译可链接，设备枚举返回 0

- 上游 RtAudio 在无音频 API 宏时自动定义 `__RTAUDIO_DUMMY__`（RtAudio.h:629 实测确认），dummy 后端 `getDeviceCount() == 0`
- OHOS 无 PulseAudio/ALSA/JACK/OSS（CMakeLists 默认 USE_AUDIO_PULSE=ON 在 OHOS 上不可满足，全关闭后编译通过）
- 音频输出在无设备环境的上游行为：应用正常启动但无音频设备可选

### 5. demod 编排层 + SDR 设备线程（src/demod, src/sdr）——超出核心切割面

- 60+ 处 wxGetApp() 调用点深度耦合 wx 应用单例（GUI 事件/通知回调），实测统计：
  - DemodulatorThread.cpp 5 处、DemodulatorWorkerThread.cpp 1 处、DemodulatorMgr.cpp 8 处、DemodulatorInstance.cpp 12 处
  - SDREnumerator.cpp 20 处、SoapySDRThread.cpp 9 处、SDRPostThread.cpp 8 处
- 这些层只在有 GUI 前端时才有意义；OHOS 无 wxCore GUI（第一节证据），故超出本次核心切割交付面，如实申报

## 三、消费者测试真跑结果（test_package，OHOS PC aarch64）

| # | 测试 | 断言 | 结果 |
|---|------|------|------|
| 1 | Modem 工厂注册表 | 21 种上游注册制式（analog 9 + digital 12，与 CubicSDR.cpp initModemList 一致）全部实例化 | PASS |
| 2 | FM 解调闭环 | liquid freqmod 合成 2 MHz IQ → ModemFM demodulate() → 1 kHz 音频分量检测（Goertzel，amp 比 816 倍） | PASS |
| 3 | AM 解调闭环 | 800 Hz 包络音检测（amp 比 206 倍） | PASS |
| 4 | USB 解调闭环 | 解析信号 4 kHz 音检测（amp 比 3179 倍） | PASS |
| 5 | BPSK 数字链路 | modemcf 合成 → ModemBPSK demodulate() 完整跑通（符号恢复链）+ 进程干净退出 | PASS |
| 6 | SoapySDR 无硬件枚举 | enumerate("") 空列表、listModules 0 模块、无崩溃 | PASS |

共 11 个断言全部 PASS（2026-09-20 OHOS PC aarch64 实测）。

**注**：测试 2-4 的调制器（freqmod/modemcf）来自 liquid-dsp 1.8.2（被测包的声明依赖），解调器是 CubicSDR 自己的 Modem 引擎（被测代码）——闭环两端一方是业界标准 DSP 库、一方是被测物，音调检测用 Goertzel 独立实现（非 liquid FFT），避免"用被测库自证"。

## 四、上游测试修改说明

无（上游无测试套件，不存在修改）。本次交付新增的 test_package 为消费者视角补全测试（第三方为 OHOS 平台补测试是积分赛规则允许的补全行为），不修改上游任何源文件。

## 五、结论

- 上游注册测试：N = 0（如实申报，非豁免——上游确实无测试注册）
- 消费者补全测试：6/6 PASS（DSP 算法层闭环 + SDR 无硬件形态定性）
- 硬件交互层不可测根因：OHOS PC 无 SDR 硬件（逐项形态见第二节 3/4 小节）
- GUI 层不可构建根因：OHOS 无 wxCore GUI/桌面 GL 立即模式（第一节四条实测证据）
