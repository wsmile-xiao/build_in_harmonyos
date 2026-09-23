# libhmsbeagle

BEAGLE is a high-performance library for evaluating phylogenetic likelihoods
(continuous-time Markov processes) of biomolecular sequence evolution.

- 上游: https://github.com/beagle-dev/beagle-lib
- 许可证: MIT
- 构建系统: CMake

## OHOS 适配要点

- HarmonyOS PC (aarch64) 采用 CPU-only 构建: 关闭 CUDA/OpenCL/JNI/SSE。
- 关闭 `BEAGLE_OPTIMIZE_FOR_NATIVE_ARCH` 避免 `-march=native` 不可移植。
- 头文件安装到 `include/libhmsbeagle-1`, 使用 `#include <libhmsbeagle/beagle.h>`。
- 消费者链接 `hmsbeagle` + `hmsbeagle-cpu`。

## 版本

- 4.0.1: 初次适配 (BEAGLE v4.0.1)。
