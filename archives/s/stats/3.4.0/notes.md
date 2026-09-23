# stats 3.4.0 适配笔记

## 编译环境
- 构建系统: custom（上游无根构建系统，纯头文件库；测试套件用上游自带 shell configure + Makefile.in）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4（OHOS 工具链）
- 状态: built（待 PR 合并后由 release 流水线发布）

## 上游结构

- 官方仓库：https://github.com/kthohr/stats ，tag v3.4.0，SHA256
  `aee9cadf0ab8c6fc26963d502eb62cd551f0e0e83388b72d61819308cc8bb17f`。
- 交付物就是 `include/stats.hpp` + `include/stats_incl/`，header-only，
  上游 README 明确唯一依赖是 GCEM（`stats.hpp` 直接 `#include "gcem.hpp"`）。
- 上游无 CMake/Autotools 主构建；`tests/setup` 把 `test_setup/configure.in`
  和 `Makefile.in` 复制进 `tests/{dens,prob,quant,rand}`，逐套件
  `./configure && make` 生成 84 个独立测试可执行文件。

## 编译步骤

1. W0：确认唯一依赖 gcem 已发布（gcem/1.18.0，PR !7601 已合入）。
2. 设备上按上游文档复现测试：`GCEM_INCLUDE_PATH=... CXX=clang++
   STATS_MATRIX_OPS="" ./configure -s && make`，84/84 通过
   （日志 ~/tmp/uc2/stats/upstream-tests.log）。
3. 配方 `build()` 用生成的 CMake driver 编译并运行全部 84 个上游测试
   （`STATS_ENABLE_STDVEC_WRAPPERS`，与上游 `./configure -s` 一致），
   `conan create` 在干净源码上复现同样结果。
4. `package()` 仅复制 `include/*.hpp`（保持上游目录结构）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 configure 默认 `CXX=g++`、链接 `-lblas -llapack`，设备均不存在 | configure.in 在非 darwin 下硬编码 gcc + blas/lapack | 环境变量 `CXX=clang++`、`STATS_MATRIX_OPS=""` 覆盖；配方内 CMake driver 用 clang++ 且不链 blas/lapack（stats 头文件本身不依赖它们） |
| 2 | `tests/setup`、`./configure` 在 sh 下不可执行 | 脚本是 bash 语法（declare -a 等） | 用 `bash setup` / `bash ./configure` 调用 |
| 3 | 09-02 旧会话在 `~/builds/stats-3.4.0.work` 留下残缺解压（仅 40 文件），导致 lang-preflight 误判 python | init-build 复用了旧 work 目录 | 从 tarball 重新干净解压后 lang-preflight 判定 cpp 231 文件 100%；误判产生的 env_unsupported result.json 由后续真实终态覆盖 |

## 源码修改

无补丁（patches 为空）。上游源码零修改。

## 依赖版本

- gcem/1.18.0（制品仓已发布，PR !7601）

## 验证结果

```bash
# 设备上按上游文档跑的完整上游测试（84 程序全部 rc=0）：
bash ~/tmp/uc2/stats/run_upstream_tests.sh   # 结果见 upstream-tests.log
# 汇总：dens 23 + prob 19 + quant 19 + rand 23 = 84/84 通过，0 失败 0 跳过

# 配方内复现（conan create 的 build() 步骤，输出 STATS_UPSTREAM_TEST[i/84]）：
conan create . -pr ci/conan/profiles/ohos-aarch64 --build=missing
```

## 注意事项

- rand 套件是统计抽样打印（均值/方差应接近理论值），上游无硬断言，
  判定以进程退出码为准——这与上游行为一致，不是本适配的放松。
- 矩阵包装器分支（arma/blaze/eigen）在上游默认配置下不编译，本次保持一致。
---

**编译结束**: 2026-09-05 15:15
**最终状态**: built
