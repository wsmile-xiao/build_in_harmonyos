# DepQBF

基于 QDPLL 的量化布尔公式（QBF）求解器，读取 prenex CNF（QDIMACS）格式，
支持冲突驱动子句学习与解驱动立方学习，并提供可增量求解的 C API。

## 功能概述

- `depqbf` 命令行求解器：求解 QDIMACS 文件，SAT 返回 10、UNSAT 返回 20
- `libqdpll.a` C API（`qdpll.h`）：建模前缀、子句增删、push/pop 与子句组增量求解、假设求解
- 依赖方案分析（standard dependency scheme）与动态 QBCE（5.0+ 默认启用）
- QDIMACS 输出（`--qdo`）与 QRP 证明轨迹（`--trace`）

## OHOS 适配

- 构建系统为纯 Makefile：`make CC=<conan-cc> -j1 libqdpll.a depqbf`，跳过 Linux `-soname` 动态库分支。
- 无外部依赖，纯 C99，clang 15 可直接构建。
- 上游 5.01 无自动化测试框架；适配后 `test_package` 新增 25 个检查点（19 API + 6 二进制），全部在真机实测。
- `depqbf --version` 输出到 stderr；求解退出码 10/20 为正常语义，测试脚本已正确处理 `set -e`。

## 依赖关系

- 编译依赖：无
- 运行依赖：无

## 参考资料

- 官网：https://lonsing.github.io/depqbf/
- 上游仓库：https://github.com/lonsing/depqbf
- 5.01 源码：https://github.com/lonsing/depqbf/archive/version-5.01.tar.gz
