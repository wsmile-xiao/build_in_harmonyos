# qqwing

## 软件简介

QQWing 是一个数独（Sudoku）谜题生成与求解库，同时提供命令行工具。上游支持 C++、Java、JavaScript 三种语言实现。本仓库适配 C++ 版本（libqqwing 库 + qqwing 命令行工具）。

## 编译版本

- 1.3.4 (2026-09-20)

## 主要功能

- 数独谜题生成（支持多种难度与对称性）
- 数独谜题求解
- 解的唯一性判断与解计数（countSolutions / hasUniqueSolution）
- 求解过程记录与提示（solveHistory / solveInstructions）

## 编译配置

### 1.3.4 版本

- 构建系统: autotools（configure + make）
- 编译器: clang / clang++
- 配置选项:
  - `--disable-shared` `--enable-static`（静态库，避免 .so 签名与运行时加载问题）
  - `--build=aarch64-linux-ohos` `--host=aarch64-linux-ohos`（OHOS triplet，绕过 config.guess）
- 补丁: `patches/0001-config.sub-ohos.patch`（config.sub 识别 linux-ohos）

## 依赖

无外部依赖（纯 C++ 标准库）。

## 安装使用

```bash
qqwing --help
qqwing --generate --one-line --difficulty simple
qqwing --solve --one-line "5.3..7...."
```

## 许可证

GNU General Public License version 2 or later (GPL-2.0-or-later)

## 相关链接

- 官方网站: https://qqwing.com/
- GitHub: https://github.com/stephenostermiller/qqwing
