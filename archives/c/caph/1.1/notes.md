# caph 1.1 — Adaptation Notes

## 软件概述

Caph 是一款基于 SDL 1.2 + libpng + OpenGL 的 2D 物理益智游戏。玩家通过绘制线条引导小球到达目标点。

## 上游信息

- **上游版本**: 1.1
- **上游源码**: https://sourceforge.net/projects/caphgame/files/caph/caphgame-1.1/caph-1.1.tar.bz2
- **许可证**: GPL-3.0-or-later
- **构建系统**: 自定义 bash 脚本 (confg → mkgen → caph.mk)
- **依赖**: SDL 1.2, libpng, OpenGL (已移除), libm

## 鸿蒙适配修改

### 1. 移除 OpenGL 依赖

- **文件**: `src/confg`
- **原因**: OHOS sandbox 无 GPU 上下文，`-D_OPENGL` 宏和 `-lGL` 链接会导致构建失败
- **修改**: 注释掉 `CFLAGS+=' -D_OPENGL'` 和 pkg-config gl 检测块

### 2. 修复 shebang

- **文件**: `src/mkgen`, `src/confg`, `src/build`
- **原因**: OHOS 没有 `/bin/bash`，导致脚本无法执行
- **修改**: `#!/bin/bash` → `#!/system/bin/sh`

### 3. 修复 SYS_DATA_DIR 路径

- **文件**: `src/caph.c`
- **原因**: conan 包布局中二进制在 `bin/`，数据在 `res/caph/`，原始路径 `../share/caph/` 不匹配
- **修改**: `../share/caph/` → `../res/caph/`

### 4. 编译标志注入

- **文件**: `conanfile.py`
- **原因**: worker 环境 pkg-config 不可用
- **修改**: 使用 `deps_cpp_info.includedirs/libdirs/libs` 获取 SDL/libpng 的编译和链接标志，通过 CC/CFLAGS/LFLAGS 环境变量传递给 mkgen

## 测试策略

- 上游无自动化测试（GUI 应用）
- 消费者测试验证：二进制完整性、数据文件完整性、链接契约、SDL dummy 驱动下 10 秒无崩溃

## 消费者测试用例

- 新增鸿蒙测试用例 1 个（test_package 中 SDL_VIDEODRIVER=dummy 运行时烟雾测试）
---

**编译结束**: 2026-09-30 21:23
**最终状态**: built
