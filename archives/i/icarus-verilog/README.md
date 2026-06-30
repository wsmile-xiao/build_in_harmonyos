# Icarus Verilog

Verilog 编译器和仿真器，用于硬件描述语言的编译和逻辑仿真。

## 简介

Icarus Verilog (iverilog) 是一个开源的 Verilog 综合和仿真工具。它将 Verilog (IEEE 1364) 源码编译为可执行仿真程序，支持行为级和 RTL 级仿真。

## 主要功能

- **iverilog**: Verilog 编译器，将 Verilog 源码编译为可执行格式
- **vvp**: Verilog 仿真运行引擎，执行 iverilog 编译产生的仿真程序
- **vhdlpp**: VHDL 预处理器（实验性支持）

## HarmonyOS 适配要点

1. GitHub tag tarball 不含 configure 脚本，需先运行 `autoconf -f` 生成（不要运行完整 `autoconf.sh`，否则 gperf 重新生成的输出会导致 clang SIGSEGV 崩溃）
2. tarball 中已有的 bison/flex/gperf 预编译输出可直接使用，不要让 make 重新生成
3. 需要修改 config.guess 和 config.sub 以识别 HarmonyOS 平台
4. `make -j1` 避免并行竞态问题

## 依赖

- gperf (≥ 3.1) — 编译时需要（bootstrap）
- autoconf (≥ 2.72) — 编译时需要（生成 configure）

## 安装

```bash
# 使用预编译包安装
curl -fsSL install.sh | sh -s -- icarus-verilog 12.0
```

## 参考

- 官网：https://iverilog.icarus.com/
- GitHub：https://github.com/steveicarus/iverilog