# fft-c for HarmonyOS

## 概述

fft-c（adis300/fft-c）是 FFTPACK 的易用 C 封装库：提供 `create_fft_transformer` /
`fft_forward` / `fft_backward` / `windowing` / cosq 变换等公开 API，
以 `double` 精度（可切换 float）对实数序列做快速傅里叶变换（FFTPACK rfftf/rfftb），
支持缩放输出（FFT_SCALED_OUTPUT）与窗函数（HANNING/HAMMING/BLACKMAN 等）。

本归档为 HarmonyOS PC (aarch64) 平台的适配记录，版本对应上游 commit `3356ecd87d`
（上游未打 tag）。归档内容：Conan 配方（含上游 bug 补丁）、test_package 消费者验证、
鸿蒙专项数值测试与上游测试枚举台账。

## OHOS 适配要点

- **构建系统**：上游无构建系统（仅演示用 Makefile 目标 `example`），配方直接用
  OHOS 工具链（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
  编译 `fft.c`，`llvm-ar` 归档，可选共享库（带 `-Wl,-soname`）。
- **上游 bug 修复**：`patches/0001-fix-fft-backward-double-scaling.patch` 修复
  `fft_backward` 在 `FFT_SCALED_OUTPUT` 下对 rfftb 结果再乘 n 导致往返变换放大
  n 倍的问题（实测 forward+backward 返回 n×原信号）。
- **rfftf 输出排布（实测）**：`out[0]=R0(DC)`，`out[N-1]=R_{N/2}(Nyquist)`，
  对 `1<=k<=N/2-1`：`out[2k-1]=R_k`，`out[2k]=I_k`（非标准 FFTPACK 排布，
  消费方需按此取 bin）。
- **依赖**：无第三方库依赖（仅 libm）。

## 产物与验证

- 库：`libfft_c.a`（静态）/ `libfft_c.so`（共享，带 DT_SONAME），头 `fft.h`
- 上游测试：无独立测试框架（example.c 为样例），全量枚举台账见版本目录 `reports/`
- 鸿蒙专项测试：`test_ohos/ohos_fft_test.c`（9 组数值断言全绿，见 `test_ohos/` 日志）
- test_package 消费者验证：9 组数值断言（频谱 bins 2/15、往返还原、HANNING 窗、cosq）
- 消费者用例：`test_consumer/`（基于已安装包的主导频率检测场景）