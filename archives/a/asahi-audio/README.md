# asahi-audio

> Apple Silicon Linux audio DSP configuration package

## 简介

asahi-audio 是 AsahiLinux 项目的一部分，为 Apple Silicon (M1/M2/M3) 设备上的 Linux 系统提供音频 DSP 配置文件。它包含 FIR 滤波器数据、WirePlumber 路由配置、PipeWire DSP 配置等，用于实现苹果设备的扬声器校准和音频路由。

## OHOS 适配要点

- 纯数据包，无 C/C++ 编译，无需任何源码修改
- 仅安装配置文件（wav/json/lua/conf）到 share/asahi-audio/、share/wireplumber/、share/pipewire/
- make 依赖 sed 工具处理 JSON 别名生成

## 依赖

无外部依赖（纯数据包）。

## 功能验证

```bash
# 检查安装的配置文件
ls ~/usr/local/share/asahi-audio/
ls ~/usr/local/share/wireplumber/
```

## 参考

- [源码仓库](https://github.com/AsahiLinux/asahi-audio)