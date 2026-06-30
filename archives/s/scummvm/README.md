# scummvm

ScummVM 是一个经典游戏引擎的跨平台重新实现，支持运行数百款经典冒险游戏。

## 描述

ScummVM（Script Creation Utility for Maniac Virtual Machine）是一个开源项目，重新实现了多种经典游戏引擎，使这些游戏能够在现代系统上运行。它支持超过 80 种游戏引擎，涵盖 LucasArts SCUMM 游戏、Sierra On-Line 游戏、Adventure Soft 等众多经典冒险游戏。

## 已编译版本

| Version | Status | Date |
|---------|--------|------|
| 2026.2.0 | built  | 2026-05-25 |

## 构建说明

- 构建系统：自定义 configure 脚本 + GNU Make
- 构建命令：`./configure --prefix=/usr/local && make -j2`
- 补丁数：2（config.guess 和 config.sub 的 HarmonyOS 适配）
- 后端：SDL2 + OpenGL (with shaders)
- 所有引擎插件编译为 STATIC_PLUGIN（无动态加载）

## 关键适配问题

1. **config.guess 不识别 HarmonyOS**：添加 HarmonyOS 检测分支，生成 `aarch64-unknown-linux-ohos`
2. **config.sub 不接受 ohos**：添加 `ohos-linux` OS 模式和 `ohos*` 系统类型识别

## 依赖

| Dependency | Version | Source |
|-----------|---------|--------|
| SDL2 | 2.30.10 | cmd-pkgs |
| FreeType2 | 2.14.3 | cmd-pkgs |
| FriBiDi | 1.0.16 | cmd-pkgs |
| libjpeg-turbo | 3.1.0 | cmd-pkgs |
| libpng | 1.6.44 | cmd-pkgs |
| zlib | 1.2.13 | system |

## 构建产物

- scummvm — 可执行文件（SDL2 后端 + OpenGL shaders）

## 使用方法

```bash
# 查看版本
scummvm --version
# Output: ScummVM 2026.2.0

# 启动游戏
scummvm /path/to/game/data

# 列出支持的引擎
scummvm --list-engines
```