# chuffed 0.13.1 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMakeLists.txt，cmake_minimum 3.5，project(CXX C)）
- 编译日期: 2026-09-08
- 编译器: clang/clang++ 15（OHOS SDK 工具链，aarch64-linux-ohos）
- 状态: built（conan create 全绿；尚未 release upload）

## 上游信息

- 上游: https://github.com/chuffed/chuffed tag 0.13.1
- 源码包: https://github.com/chuffed/chuffed/archive/refs/tags/0.13.1.tar.gz
  sha256: 7408d35e85559ecbf4b5b7ef8aa2278e536b1231dc29e18b0b2f9a7e878a1bc0
- 许可证: MIT（Copyright (c) 2015 geoffchu）

## 编译步骤

1. 下载源码包并校验 sha256
2. `conan create archives/c/chuffed/0.13.1 --profile=ohos-aarch64 --build=missing`
3. CMake 配置由 CMakeToolchain 生成：
   - CP_PROFILER=OFF（CP Profiler 可选集成，制品仓无此依赖，关闭后零依赖）
   - SUPPORT_VAR_IMPACT=OFF（上游默认值，impact branching 为可选实验特性）
   - STATIC=OFF（不向链接器传 -static，产物由 Conan 管理依赖链）
   - CMAKE_DISABLE_FIND_PACKAGE_ZLIB=True（ZLIB 仅被 3 个 EXCLUDE_FROM_ALL 示例使用，示例不属于安装集）
   - BUILD_SHARED_LIBS=OFF（静态库交付）
4. 构建产物：libchuffed.a + libchuffed_fzn.a + fzn-chuffed（bin/）
5. `cmake --install` 安装：lib/（两静态库）+ include/chuffed/（全量头文件）+ bin/fzn-chuffed + share/minizinc/（mznlib 与 chuffed.msc solver 配置）+ lib/cmake/chuffed/（上游导出的 CMake config）

## 上游测试框架核验（rule4 纪律）

**上游 chuffed 0.13.1 无测试套件，注册测试数 N=0。实测证据：**

1. **源码树核验**：tag 0.13.1 完整源码树（tarball 解包 + GitHub API `git/trees/0.13.1?recursive=1`，`truncated: false`）中**不存在任何 test/tests 目录**，全树无 test 相关路径（find . -iname "*test*" 结果为空）。
2. **CMake 注册核验**：上游 CMakeLists.txt 全文无 `enable_testing()`/`add_test()`/`include(CTest)`，无任何测试目标注册。
3. **上游 CI 佐证**：`.github/workflows/cmake.yml` 中测试步骤为 `# TODO: Run Chuffed tests`——上游官方 CI 也只构建不跑测试，印证 0.13.1 发布时无测试套件。
4. **上游自述**：README 无运行测试的说明；`chuffed/mzn-models/` 是 MiniZinc 模型示例（5 个 .mzn），`chuffed/examples/` 是 25 个 C++ API 示例（全部 EXCLUDE_FROM_ALL，不属于默认构建目标、不属于安装集），均非注册测试用例。

**结论**：N=0 如实申报。上游无测试可跑（无测试框架、无注册测试目标），非"测试存在但跑不了"。已按审核口径（示例不算测上游）不计 examples/mzn-models 为上游测试；补全验证由 test_package 承担（见下）。

## test_package（补全测试）

`test_package/` 通过公开 C++ API 实测求解器核心行为（上游 examples/queens.cpp 同款 API 用法）。chuffed 引擎是进程级全局单例（一进程解一题，上游 fzn-chuffed 的 main() 也只调一次 engine.solve），故两个场景各自独立进程：

1. **test_package（satisfy 场景）**：6-Queens 全解搜索，`so.nof_solutions = 0` 枚举全部解，断言恰为已知 4 解（engine.solutions == 4）+ 搜索树非空（engine.nodes > 0）——2 断言
2. **test_optimize（optimize 场景）**：x+y≤10 且 x−y=2、x∈1..9 上 `optimize(v[0], OPT_MAX)` maximize x，断言产出解（engine.solutions ≥ 1）+ 已知最优 best_sol==6（与 fzn-chuffed 二进制独立求解结果一致）——2 断言
3. 覆盖 API：createVars/all_different/all_different_offset/int_linear/branch/output_vars/optimize/engine.solve/Problem::print——引擎、建模、分支、优化四层 API 均真实调用

实测（HarmonyOS PC arm64，本机即目标设备，conan create 内真实执行）：**4/4 断言全过**，test_package 与 test_optimize 双双 PASSED（conan create rc=0，70 个编译单元）。

另在设备上直接实测 `fzn-chuffed` 二进制：`--help` 正常输出；求解 satisfy 问题（-a 枚举 4 解全对）与 maximize 问题（最优 x=6 y=4）均正确，rc=0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 交叉构建第一次尝试无报错一次通过 | 上游 CMake 无平台硬编码 | 零补丁零源码修改 |
| 2 | fzn-chuffed 运行报 `Error loading shared library libc++_shared.so` | OHOS clang 动态链接 libc++_shared.so，运行时需工具链 lib 路径 | test_package generate() 从 tools.build:compiler_executables 自省定位工具链 aarch64-linux-ohos/c++ 目录前置到 LD_LIBRARY_PATH（scope=run，R33 合规不裸用 shell 变量） |
| 3 | 手写 FlatZinc 带 output 项报语法错误 | 上游 parser.yxx 语法为 `preddecl_items vardecl_items constraint_items solve_item ';'`，不支持 output 项（chuffed 的输出走 output_var 注解） | 测试用 output_var 注解（标准 FlatZinc 输出方式），符合上游解析器设计 |
| 4 | 同进程连续两次 engine.solve，第二次 optimize 结果错乱（solutions 复用、best_sol=-1） | chuffed 引擎是进程级全局单例，设计为一进程解一题（上游 fzn-chuffed 同样只 solve 一次） | test_package 拆两个独立二进制：test_package（satisfy）+ test_optimize（optimize），各自进程内单次 solve |
| 5 | test() 直接 self.run 二进制报无法执行 | OHOS /system/bin/sh (mksh) 不能直接执行 ELF | 用 CONFIG_SHELL bash 包装执行（c-ares 1.34.5 同款先例） |
| 6 | CMake configure 输出 "System is unknown to cmake" 警告 | CMake 4.x 对 HarmonyOS 无内置 Platform 模块，仅提示不阻断 | 无需处理，配置与构建正常完成（仓库既有包同样现象） |

## 源码修改

**无**。零补丁、零源码修改（conandata.yml 无 patches 段）。

## 依赖版本

无外部依赖（W0 天然通过）。构建期仅用 CMake + OHOS clang；上游可选依赖（CP Profiler、ZLIB for 3 examples）全部关闭/禁用，运行期仅 pthread。
