# bsc

bsc（Bluespec Compiler）是 Bluespec SystemVerilog（BSV）/ Bluespec Haskell（BH）硬件描述语言的编译器，将高级硬件描述综合为可综合的 Verilog（用于 FPGA/ASIC 工具链）或 Bluesim C++ 仿真模型。上游为 B-Lang-org/bsc（Bluespec 开源社区维护），版本号采用 `YYYY.MM` 日期式发布。

## 功能概述

- 编译 BSV/BH 硬件描述语言，执行类型检查、调度与综合
- 生成可综合 Verilog（对接 Quartus/Vivado 等后端）
- 生成 Bluesim C++ 仿真器（内置 VPI/Verilator 交互支持）
- 附带 Bluetcl（Tcl 脚本接口）与上游标准库 `Libraries`（Prelude 等）

## OHOS 适配状态

- **阻塞**：编译器核心为 Haskell 实现，源码构建要求 GHC 7.10.3–9.12 + 5 个 Hackage 包（regex-compat、syb、old-time、split、strict-concurrency）+ libgmp
- OHOS 主机为纯 musl 环境，GHC 官方 aarch64 bindist 均为 glibc 动态链接，无法运行；上游亦无 linux-arm64 官方二进制（pandoc 的 use-binary-release 路径不可用）
- 详见 [2026.01/notes.md](2026.01/notes.md)

## 依赖关系

- 源码构建（当前阻塞）：GHC、cabal、gmp、pkg-config、GNU Make、Tcl（可选 Bluetcl）
- 详见版本目录 manifest.yaml

## 参考资料

- 源码: https://github.com/B-Lang-org/bsc
- 文档: https://github.com/B-Lang-org/bsc/tree/main/doc
- 许可证: BSD-3-Clause（主体，详见源码 COPYING 与 LICENSES/）
