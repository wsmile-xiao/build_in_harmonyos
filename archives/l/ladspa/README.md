# ladspa

LADSPA (Linux Audio Developer's Simple Plugin API) 是 Linux 音频开发者简易插件 API 的参考实现。

## 描述
ladspa 包含 LADSPA 插件 API 的头文件和参考实现工具。LADSPA 是一个轻量级的音频插件标准，为音频处理应用提供统一的插件接口。

## 已编译版本
- 1.17 (2026-06-01)

## 依赖
- 无外部依赖（纯 C 项目）

## 特性
- 提供 ladspa.h 头文件
- 提供 applyplugin 命令行工具
- 提供 listplugins 工具

## 使用方法
```bash
# 列出可用插件
listplugins

# 应用插件处理音频
applyplugin input.wav output.wav plugin.so:label:param1:param2
```