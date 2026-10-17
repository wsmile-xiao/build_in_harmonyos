# puzzles

> Simon Tatham 的可移植益智游戏合集（Portable Puzzle Collection），37 个单人小游戏的 C 语言实现。

## 简介

puzzles 是一组经典的逻辑益智小游戏，包括数独（Solo）、黑白棋（Reversi 变体/Flip）、扫雷（Mines）、填字游戏（Tents）、华容道（Fifteen）、桥接（Bridges）、填格子（Loopy）、数回（Slant）等 37 个正式游戏。上游同时提供每个游戏的独立解算器（*solver）、命令行生成/校验工具与辅助算法自检程序。

本仓库提供 puzzles `20260720.3c36322` 在 HarmonyOS（OpenHarmony）PC aarch64 平台的 Conan 配方，构建产物为每个游戏一个的命令行可执行文件（`bin/<game>`），外加辅助自检程序与 fuzzpuzz。

## OHOS 适配要点

- HarmonyOS PC 不提供 GTK+ 工具包，上游 unix 平台默认的 GTK 前端不可用。适配新增 **headless 命令行前端 `ohos.c`**（约 350 行，仿 gtk.c 的 `--generate/--test-solve/--list-presets/--time-generation/--save` 模式），不依赖任何 GUI 工具包即可完成生成、求解、序列化全链路。
- `cmake/setup.cmake` 新增 `HarmonyOS/OHOS` 平台分支（在 emcc 分支之后、unix 分支之前），include 新的 `cmake/platforms/ohos.cmake`。
- `ohos.cmake` 定义 OHOS 平台特性：`build_gui_programs=FALSE`、`build_individual_puzzles=TRUE`、`build_cli_programs=TRUE`，puzzle 二进制经 install 规则进入 `bin/`（与 unix 平台布局一致）；`no-icon.c` 提供链接期图标符号。
- 随机源：`get_random_seed` 读取 `/dev/urandom`（bionic libc），不可用时回退到 time+pid 混合种子，保证受限环境下仍可生成。
- 测试体系：上游 auxiliary 自检程序（10 项单元测试）+ 34 个可求解游戏的 `--test-solve` + fuzzpuzz 冒烟 + OHOS 前端 CLI 全链路（5 项），共 50 场景。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| （无） | — | 纯 C 项目，仅链接 libm；无第三方库依赖 |

## 功能验证

```bash
solo --version
# 输出: Solo, from Simon Tatham's Portable Puzzle Collection
solo --list-presets | head -3
# 输出: 2x2 2x2 Trivial
#       2x3db 2x3 Basic
#       3x3 3x3 Trivial
solo --test-solve --generate 1 3x3 && echo OK   # 生成+求解通过
```

## 参考

- [上游网站](https://www.chiark.greenend.org.uk/~sgtatham/puzzles/)
- [上游 git 仓库](https://git.tartarus.org/simon/puzzles.git)
