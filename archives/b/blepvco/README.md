# blepvco

blepvco 是 Sean Bolton 编写的一组 LADSPA 振荡器插件（3 个实例：Sync-Saw-VCO、Sync-Rect-VCO、Sync-Tri-VCO），面向模块化软合成器（如 Alsa Modular Synth），特点是抗混叠的 band-limited 波形与 hard-sync 支持。

## 功能概述

- 3 个 LADSPA 音频插件：锯齿（Sync-Saw）、方波/脉冲（Sync-Rect）、三角（Sync-Tri）硬同步 VCO
- 使用预生成的 minBLEP（minimum-phase band-limited step）数据表做抗混叠波形过渡
- 线性/指数频率调制、1V/oct、semitone、sync 输入等调制端口
- 无 GUI，纯 DSP 计算；由任意 LADSPA 宿主经 `dlopen` + `ladspa_descriptor()` 加载

## OHOS 适配

- 插件为自包含共享库（仅依赖 libc / libc++_shared），dlopen 即用，无桌面/JACK 依赖
- 上游 Makefile 链接规则硬编码 `g++`；补丁将其改为可覆盖的 `$(CXX)`，编译器由 Conan profile 的 `tools.build:compiler_executables` 提供
- 上游 `CPPFLAGS += -I. -fPIC -D_REENTRANT -Wall -O3` 原样保留，无需其他源码改动
- 上游无测试套件；test_package 提供 dlopen 冒烟宿主，遍历 3 个描述符并执行 instantiate/activate/run/deactivate/cleanup

## 依赖关系

- 编译依赖：`ladspa-sdk/1.17`（提供 `ladspa.h` API 头文件）
- 运行依赖：无（宿主负责 dlopen；插件自身无外部共享库依赖）

## 参考资料

- 主页与发布归档：https://www.smbolton.com/linux.html
- 归档直链：https://www.smbolton.com/linux/blepvco-0.1.0.tar.gz
- LADSPA API：https://www.ladspa.org/
