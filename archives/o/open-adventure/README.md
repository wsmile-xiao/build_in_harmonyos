

经典的文本冒险游戏（Colossal Cave Adventure）的开源重实现版本，由 Eric S. Raymond 维护。

## 软件简介

open-adventure 是 Will Crowther 和 Don Woods 于 1976 年创作的经典文本冒险游戏"Colossal Cave Adventure"的开源版本。这是最早的冒险游戏之一，也是整个冒险游戏类型的起源。

主要特性：
- 纯文本界面，支持命令行编辑（通过 libedit）
- 支持保存/恢复游戏进度
- 包含作弊模式（cheat 命令）用于调试
- 115 个功能测试用例
- 跨平台 C99 实现

## 编译版本

| 版本 | 状态 | 编译日期 | 预编译包 |
|------|------|----------|----------|
| 1.20 | published | 2026-06-17 | open-adventure-1.20-ohos-aarch64.tar.gz |

## 编译依赖

- libedit (行编辑库)
- ncurses (终端 UI 库)

## 二进制产物

- `advent` — 主游戏程序
- `cheat` — 调试/作弊工具

## 注意事项

- 本软件为纯 Makefile 构建，无 configure 脚本和 install 目标
- libedit 和 ncurses 静态链接进二进制，运行时无需额外安装这两个库
- 验证方法：运行 `advent` 或 `advent -h` 查看输出
