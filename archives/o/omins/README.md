# omins

Omins 是一组面向模块化合成器的 LADSPA 插件，提供包络、控制/音频信号转换、比较、交叉淡化、采样保持、概率切换、波导网格等 DSP 模块。

## 功能概述

- 18 个可独立加载的 LADSPA 共享对象
- 共导出 28 个 LADSPA 插件描述符
- 纯 C DSP 实现，无 GUI、JACK 或桌面环境依赖
- 由 LADSPA 宿主通过 `dlopen()` 和 `ladspa_descriptor()` 加载

## HarmonyOS PC 适配

- 使用 Conan 的 OHOS/aarch64 Clang 配置执行 Autotools 构建
- 通过 `ladspa-sdk/1.17` 提供标准 `ladspa.h`
- 重新生成老旧 Autotools 文件，使 `aarch64-unknown-linux-ohos` 三元组可被识别
- 针对 HarmonyOS PC 的 HMDFS 权限语义，将生成的 `configure` 中临时目录 umask 从 `077` 调整为 `022`
- 测试宿主在真机加载全部 18 个共享对象，遍历并运行全部 28 个描述符

## 依赖关系

- 构建/接口依赖：`ladspa-sdk/1.17`
- 构建工具：`automake/1.18`、`libtool/2.5.4`
- 运行依赖：系统 C 运行库与数学库

## 上游

- 项目主页：https://www.nongnu.org/om-synth/omins.html
- 官方源码：https://download.savannah.nongnu.org/releases/om-synth/omins-0.2.0.tar.gz
