# caph — Physics-Based Puzzle Game

## 概述

Caph 是一款基于 SDL 1.2 + libpng 的 2D 物理益智游戏。

- **上游**: http://caphgame.sourceforge.net/
- **许可证**: GPL-3.0-or-later
- **类型**: 应用程序 (application)

## 适配版本

| 版本 | 状态 | 依赖 |
|------|------|------|
| 1.1 | 已适配 | sdl/1.2.15, libpng/1.6.58.3 |

## 鸿蒙适配要点

1. 移除 OpenGL 依赖（OHOS sandbox 无 GPU 上下文），改用 SDL 软件渲染
2. 修复 bash shebang 为 `#!/system/bin/sh`
3. 修复数据路径 `SYS_DATA_DIR` 匹配 conan 包布局
4. 使用 `deps_cpp_info` 获取依赖编译标志（不依赖 pkg-config）

## 测试

- 上游无自动化测试（GUI 交互应用）
- 消费者测试覆盖：二进制完整性、数据文件完整性、链接契约、运行时烟雾测试
