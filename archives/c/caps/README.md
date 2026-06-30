# caps

> LADSPA audio effects plugin library

## 简介

caps 是一套基于 LADSPA（Linux Audio Developer's Simple Plugin API）标准的音频效果插件库，提供放大器模拟、压缩器、EQ、延迟、混响等多种效果处理器。广泛用于 Linux 音频处理管线中。

## OHOS 适配要点

- 使用自定义 configure.py + Makefile 构建系统，不是标准 autotools/cmake/meson
- glibc 特定类型名（__int8_t 等）在 musl/OpenHarmony 不存在，需用 #ifdef __OHOS__ 替换为标准 int8_t
- GCC 内置函数（__builtin_sinf）作为模板参数不被 clang 支持，需替换为 sinf/cosf
- GNU 扩展 exp10f 在 musl 不提供，需定义为 powf(10.0f, x)
- configure.py 需添加 OHOS 平台检测，跳过 SSE 和 make clean

## 依赖

无外部依赖（自包含构建）。

## 功能验证

```bash
# caps 是 LADSPA 插件库，验证 .so 文件存在
ls ~/usr/local/lib/caps/
listplugins ~/usr/local/lib/caps/*.so
```

## 参考

- [官方主页](https://quitte.de/dsp/caps.html)