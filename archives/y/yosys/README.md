# Yosys — 开源 Verilog RTL 综合框架

[Yosys](https://github.com/YosysHQ/yosys)（Yosys Open SYnthesis Suite）是开源
Verilog RTL 综合框架：把 Verilog/SystemVerilog 前端、大量独立优化 pass 和
脚本化流程组合起来，完成从 RTL 到门级网表的综合，并支持形式等价验证（SAT/SMT）。
配套的 ABC 负责逻辑优化与工艺映射。

- 上游主仓：https://github.com/YosysHQ/yosys
- 许可证：ISC
- 语言：C++（自带 Makefile 构建系统）
- 产物：`bin/yosys`（主程序）、`bin/yosys-config`、`bin/yosys-filterlib`、
  `bin/yosys-smtbmc`、`bin/yosys-witness`、`share/yosys/`（techlibs 与 pass 脚本）

## 功能概述

- 读入 Verilog-2005 / SystemVerilog（部分）/ RTLIL / BLIF / JSON 等
- `synth` 系列综合脚本（generic / ice40 / xilinx / ecp5 / gowin / …）
- `sat`、`equiv_opt`、`equiv_make` 等形式验证 pass
- `write_verilog` / `write_json` / `write_blif` / `write_edif` 等后端
- TCL 脚本、插件（`-m`）、C++ 插件 API

## OHOS 适配要点

- **构建系统是自带 Makefile**：没有 configure/cmake，依赖注入只能通过
  `CXXFLAGS`/`LIBS` 的**环境变量前缀**（`Makefile:107` 是 `CXXFLAGS := $(CXXFLAGS) …`，
  会读环境值并保留 `-I.`；用 make 命令行赋值反而会覆盖掉 `-I.`）。
- **编译器必须显式传**：Makefile 自己给 `CXX`/`CC` 赋值（不是 `?=`），
  profile 的 `tools.build:compiler_executables` 不会生效，交叉编译会静默编出宿主对象，
  链接阶段报 `skipping incompatible …/libtcl8.6.so`。
- **ABC 走外部二进制**：上游 tag 归档的 `abc/` 子模块为空（0 文件），无法树内构建。
  用 conan 的 `abc` 包 + `ABCEXTERNAL`，并 `DISABLE_SPAWN=0`；
  `abc` 声明为 host requirement，`package_info()` 导出 `ABC` 环境变量供消费者运行时使用。
- **cxxopts 头文件**：`libs/cxxopts/` 子模块同样为空，但 `kernel/driver.cc` 按树内路径
  include；构建期从 conan `cxxopts` 包复制头文件到 `libs/cxxopts/include/`。
- **安装期 strip**：`make install` 用 `$(STRIP)`（默认宿主 `strip`），交叉编译时
  无法识别 aarch64 ELF，需传 OHOS SDK 的 `llvm-strip`。
- **OHOS 无 /bin/sh**：`CONFIG_SHELL` 指向 `/data/service/hnp/bin/bash`；
  `Makefile:441` 硬编码调用 `tclsh`，需提供 `tclsh` → `tclsh8.6` 的 shim。
- **bison 的 m4**：制品仓 `bison/3.8.2` 硬编码 `/data/service/hnp/bin/m4`，
  非鸿蒙设备上该路径不存在时需 `M4=` 指向系统 m4（CI 上该路径存在，此分支不触发）。

## 依赖关系

运行/链接依赖（host）：`readline`（交互式命令行编辑）、`libffi`（TCL 的 ffi 支持）、
`tcl`（TCL 脚本绑定与 tclsh）、`zlib`（压缩输出）、`cxxopts`（命令行解析，头文件）、
`abc`（逻辑优化/工艺映射，运行期 exec 的外部二进制）。

构建工具依赖（build）：`flex`（词法分析器生成）、`bison`（语法分析器生成）。

> 具体版本号以各版本目录的 `manifest.yaml` / `conanfile.py` 为准（软件级文档不固定版本）。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.66 | built | 上游 tag v0.66；自带 Makefile；ENABLE_ABC=1 + 外部 ABC |
