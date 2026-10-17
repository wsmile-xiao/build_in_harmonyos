# kicad-library-symbols 10.0.5 适配笔记

## 软件形态

KiCad 官方原理图符号库数据包：223 个 `*.kicad_symdir` 目录（每符号一个
`.kicad_sym` 文件）、全局 `sym-lib-table`、SPICE 仿真模型
`Simulation_SPICE.sp`。无任何 C/C++ 源码，上游 CMake 工程声明
`project(kicad-symbols NONE)`（不启用任何语言，无编译产物）。

## 构建环境

- 构建系统: CMake（上游 `cmake_minimum_required(VERSION 3.12)`，设备 cmake 4.1.2 兼容）
- 构建日期: 2026-09-18
- 编译器: 不涉及（project NONE，无编译步骤）
- Python: 打包脚本 `tools/kicad_lib_pack.py` 为纯标准库实现（argparse/enum/
  logging/os/re/dataclasses/pathlib/typing，使用 `str | None` 语法需 Python
  >= 3.10），设备 python3 3.12.9 满足
- 状态: built

## 构建步骤

1. `conan create` → source() 从 gitlab.com tag 归档下载（SHA256 固定于 conandata.yml）。
2. build() 用 CMake 配置 + 构建。默认 `-DKICAD_PACK_SYM_LIBRARIES=ON`
   （上游默认值）：构建期自定义目标 `pack_symbols` 调用上游自带 Python 脚本
   把每个 `.kicad_symdir` 目录打包成单文件 `*.kicad_sym`，并生成打包版
   `sym-lib-table`。
3. package() 执行 CMake install（COMPONENT resources），按上游默认
   `KICAD_DATA=share/kicad` 布局安装；LICENSE.md 单独补齐到 `licenses/`。

## OHOS 适配要点

- 纯数据包，无交叉编译问题；`package_id()` 清空（数据与架构/编译器无关）。
- CMake 的 `find_package(Python3 COMPONENTS Interpreter)` 依赖 PATH 中的
  python3；CI profile 的 [buildenv] PATH 已前置设备 python3 所在目录。
- 打包脚本对 s-expression 文本做逐行解析（非完整解析器），与上游行为一致，
  未做任何源码修改；无补丁。
- 回退方案：目标环境无 Python3 时可改配 `-DKICAD_PACK_SYM_LIBRARIES=OFF`，
  原样安装 `.kicad_symdir` 目录树；test_package 数据校验对两种安装模式均兼容。

## 上游测试情况

上游仓库**无自动化测试套件**。上游 CI（.gitlab-ci.yml）仅调用
kicad-library-utils 对符号做 KLC 规范静态检查，不构成本仓可执行的官方测试。
验证改为 test_package 数据完整性校验：符号库文件存在且 s-expression 结构
完好（首行 `(kicad_symbol_lib`、尾行 `)`、至少含一个 symbol）、关键库
（Device/power/Connector/MCU_ST_STM32F4/Simulation_SPICE）齐全、
`sym-lib-table` 可解析且条目完整、`.sp` 仿真模型已安装。

## 交付物

- `share/kicad/symbols/*.kicad_sym`：打包后的符号库（含 `*.sp` 仿真模型）
- `share/kicad/template/sym-lib-table`：全局符号库表
- `licenses/LICENSE.md`：CC-BY-SA-4.0 许可证文本

## 注意事项

该包不产生可执行文件与链接库，不需要 `commands.json`；下游消费方式是把
`share/kicad` 指向 KiCad 的数据目录（或通过 `resdirs` 定位）。

---

**编译结束**: 2026-09-18
**最终状态**: built
