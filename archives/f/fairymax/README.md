# fairymax

棋类变体 AI 引擎，支持国际象棋变体、象棋（Xiangqi）、沙特兰兹（Shatranj）和 Makruk 等。

## 简介

Fairy-Max 是一个紧凑的棋类引擎，通过 XBoard/WinBoard 协议支持多种棋类变体。
它设计用于与支持 XBoard 引擎协议的图形化棋类界面配合使用。

本包包含三个引擎变体：
- **fairymax**: Fairy-Max（通用棋类变体引擎，版本 5.0b）
- **shamax**: ShaMax（沙特兰兹/古波斯象棋，版本 5.0b）
- **maxqi**: MaxQi（象棋/中国象棋，版本 4.8）

## 版本

5.0b（maxqi 子版本为 4.8）

## 构建系统

makefile（plain Makefile，无 configure 脚本）

## 许可证

Public Domain（公有领域）

## 依赖

无外部依赖。纯 C 单文件程序，仅依赖 libc。

## 编译配置

```bash
make CC=clang CFLAGS="-fPIC -O2" prefix=$DEFAULT_PREFIX fairymax shamax maxqi fairymax.6.gz
```

注：上游 Makefile 默认 CFLAGS 含 `-s`（strip），编译时需覆盖为 `-fPIC -O2`，
由 packaging 管线统一处理 strip 和 ELF 签名。

## 安装产物

### 二进制文件
- fairymax — 55680 字节（棋类变体 AI）
- shamax — 55680 字节（沙特兰兹 AI）
- maxqi — 39296 字节（象棋 AI）

### 数据文件
- fmax.ini — 42638 字节，1164 行（Fairy-Max 棋类变体配置）
- qmax.ini — 878 字节，34 行（MaxQi 象棋配置）
- makruk.hash — 1152 字节（Makruk 哈希表）

### 插件配置
- fairymax.eng / shamax.eng / maxqi.eng（XBoard 引擎描述文件）
- fairymax.png / shamax.png / maxqi.png（引擎 logo）

### 文档
- fairymax.6.gz（man page，由 pod2man 从 fairymax.pod 生成）

## 使用方式

fairymax 使用 XBoard 协议，不支持常规 CLI 参数（如 --help/--version）。
典型测试方式：

```bash
printf "xboard\nprotover 2\nquit\n" | fairymax
# 输出: tellics say     Fairy-Max 5.0b
# 输出: tellics say     by H.G. Muller
```

需配合 XBoard 兼容的图形界面（如 xboard、eboard 等）使用。