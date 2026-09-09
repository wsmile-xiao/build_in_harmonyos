# chuffed

Chuffed 是一个约束规划（Constraint Programming）求解器，实现 Lazy Clause Generation（LCG，惰性子句生成）技术：在传统 CP 传播搜索的基础上学习 nogood 子句，把 CP 与 SAT 求解的优势结合起来。由 Monash 大学开发，曾获 MiniZinc 挑战赛冠军，是 MiniZinc 工具链的常用后端求解器之一。

## 功能概述

- 完整的 CP 求解引擎：整数/布尔变量域、传播器、分支搜索
- LCG：冲突分析、nogood 学习、VSIDS 活动度搜索、重启策略
- 丰富的全局约束：all_different、cumulative、circuit、regular、table、MDD、MST/树约束等
- FlatZinc 前端（libchuffed_fzn + fzn-chuffed 可执行文件），可直接作为 MiniZinc 后端
- C++11 代码库，纯 CMake 构建，零外部运行时依赖（仅 pthread）

## OHOS 适配

- 构建系统为 CMake（cmake_minimum 3.5，project CXX C），零外部依赖可直接构建
- 0.13.1 适配零补丁零源码修改：上游 CMakeLists 无平台硬编码，HarmonyOS 交叉编译一次通过
- CP_PROFILER=OFF（可选集成不引入）、SUPPORT_VAR_IMPACT=OFF（上游默认）、STATIC=OFF
- 产物：libchuffed.a（引擎）+ libchuffed_fzn.a（FlatZinc 前端）+ fzn-chuffed（求解器可执行文件）
- fzn-chuffed 在设备上实测可求解 satisfy/maximize FlatZinc 问题
