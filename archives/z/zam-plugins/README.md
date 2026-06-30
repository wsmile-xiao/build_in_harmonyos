# zam-plugins

zam-plugins 是 ZamAudio 开发的音频效果器插件集，提供 LV2/LADSPA/VST/CLAP 格式插件。

## 功能概述

- 18个音频效果器插件（压缩、均衡、延迟、失真等）
- 支持 LV2、LADSPA、VST2、VST3、CLAP 插件格式
- 基于 DPF (DISTRHO Plugin Framework) 构建

## OHOS 适配

- **构建系统**: makefile (DPF Plugin Framework)
- **GUI禁用**: 无X11/Wayland显示后端，DSP-only构建
- **29个补丁**: DGL守卫、pthread空操作、JACK/AU移除等
- **子模块**: DPF和pugl需手动下载

## 运行依赖

- LV2 host 或 LADSPA host
- fftw3f (ZamHeadX2/ZamNoise/ZamVerb)

## 参考资料

- 源码: https://github.com/zamaudio/zam-plugins
- 版本: 4.5
