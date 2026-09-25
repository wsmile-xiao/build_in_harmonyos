# KiCad Symbol Libraries

KiCad 官方原理图符号库集合（kicad-library-symbols），为 KiCad EDA 提供覆盖
通用元件、MCU、连接器、电源、射频等 223 个分类、上万个符号的原理图符号
数据，附全局符号库表与 SPICE 仿真模型。**纯数据包**：不含任何 C/C++ 源码
或编译产物。

## 功能概述

- 223 个 `*.kicad_symdir` 符号库目录（每符号一个 `.kicad_sym` 文件）
- 全局 `sym-lib-table`：KiCad 启动时的默认符号库注册表
- `Simulation_SPICE.sp`：SPICE 仿真专用符号（电压/电流源、地等）
- 上游 CMake 安装型工程：默认在构建期用自带 Python 脚本把 symdir 目录打包
  为单文件 `*.kicad_sym`（`KICAD_PACK_SYM_LIBRARIES=ON`），也可关闭打包
  原样安装目录

## OHOS 适配

- 纯数据负载，与架构/编译器无关，`package_id()` 清空；无交叉编译问题
- 构建期打包需要 Python3 解释器（上游脚本为纯标准库、要求 Python >= 3.10）；
  CI profile 的 buildenv PATH 提供设备 python3；不可用时回退
  `-DKICAD_PACK_SYM_LIBRARIES=OFF`（安装 `.kicad_symdir` 目录树）
- 安装布局遵循上游默认 `KICAD_DATA=share/kicad`：符号库位于
  `share/kicad/symbols`，全局表位于 `share/kicad/template/sym-lib-table`
- 上游无自动化测试套件（上游 CI 仅做 kicad-library-utils KLC 静态规范检查）；
  本仓验证为 test_package 数据完整性校验

## 依赖关系

- 构建依赖：CMake >= 3.12、Python3（仅打包模式需要）
- 运行依赖：无（数据文件）；由 KiCad 等原理图工具按 `sym-lib-table` 消费

## 参考资料

- 上游仓库: https://gitlab.com/kicad/libraries/kicad-symbols
- 许可证: CC-BY-SA-4.0（数据内容许可证，非代码许可证）
- KiCad 官网: https://www.kicad.org
