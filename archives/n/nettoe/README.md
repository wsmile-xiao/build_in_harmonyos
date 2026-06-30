# nettoe

网络井字棋游戏 (Network Tic Tac Toe)

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.5.1 | published | 2026-06-29 |

## 描述

nettoe 是一款基于终端的网络井字棋游戏，支持人机对战和网络对战。
- 官方主页: http://nettoe.sourceforge.net/
- 许可证: GPL-2.0-or-later
- 语言: C
- 构建系统: autotools

## 依赖

- ncurses (静态库，系统自带)
- 无其他外部依赖

## 构建

```bash
./configure --prefix=$PREFIX
make -j2
make install
```

## HarmonyOS 适配

### 平台问题与修复

1. **config.guess 不识别 HarmonyOS (E007)**: 更新 config.guess/config.sub 至 2023 版本 (来自 automake 1.17)，正确识别 `aarch64-unknown-linux-ohos`
2. **umask 077 权限拒绝**: HarmonyOS 文件系统中 umask 077 创建的目录无法写入文件，修改为 umask 022
3. **重复符号定义**: game.h 中全局变量未使用 extern 声明，导致多个编译单元重复定义，改为 extern + 集中定义

### 补丁列表

| 补丁 | 类型 | 说明 |
|------|------|------|
| 0001-build-aux-config.guess.patch | portability | HarmonyOS 平台检测 |
| 0002-build-aux-config.sub.patch | portability | HarmonyOS 平台检测 |
| 0003-configure.patch | portability | umask 权限修复 |
| 0004-src-game.h.patch | portability | 重复符号修复 |
| 0005-src-nettoe.c.patch | portability | 变量定义补充 |
