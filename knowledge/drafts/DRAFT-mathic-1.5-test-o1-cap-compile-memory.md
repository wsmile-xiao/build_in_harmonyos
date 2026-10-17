# 受限 worker 上测试可执行文件编译峰值内存超限：仅封顶非交付测试目标 -O1

> DRAFT-mathic-1.5-test-o1-cap-compile-memory
> （知识库扩展草稿，路径 B）与 mathic 1.5 归档同 PR 交付。

## 现象

在共享受限 OHOS worker 上编译 `mathic-unit-tests`（gtest + 模板密集的 4 个 TU，
经 `gtest_discover_tests` 展开）时，串行 `-j1` 仍报：

```
/bin/sh: Out of memory
```

有时表现为 Signal 9（SIGKILL），stdout/stderr 均为空、无编译器错误行——只有
"进程被内存压力杀掉"这一个事实可观测。mathic 1.4 第 10 轮实测：先 `-j1` 串行
封顶仍复现，随后仅把测试目标编译优化降为 `-O1` 才通过。

## 根因

1. **单进程峰值**：Release(-O3) 下 clang 编译「模板 + gtest 头」的单个编译单元
   峰值内存就已超受限 worker 限额。`-j1` 只能压住*多进程并发*的峰值，压不住
   *单进程编译一个 TU* 的峰值。
2. **可分离设置**：交付的 `libmathic.a` 与测试可执行文件是两个不同 CMake 目标，
   优化等级彼此独立，可以只动测试目标。

## 对策（mathic 1.5 patch 0003 实测）

```cmake
# src/CMakeLists.txt 末尾：仅对非交付测试目标封顶（后出现的 -O1 覆盖 Release -O3）
target_compile_options(mathic-unit-tests PRIVATE -O1)
```

配套：

```python
# conanfile.py build()：先串行封顶多进程峰值
cmake.build(build_tool_args=["-j1"])
# 再以 ctest 全量实跑判定（-N 对账 + --output-on-failure），不只看退出码
```

**边界**：测试源码与断言零改动；不引入平台宏（R8）；交付库保持 Release 优化；
不得把 -O1 当作掩盖真实编译错误的手段——最终必须以 ctest 全量实跑结果为准。

## 验证（本轮 mathic 1.5）

- conan-verify G2 / finish W3 conan create 实跑：`ctest -N` Total Tests 14，
  `ctest --output-on-failure` 14/14 Passed，0 failed，0 skipped。
- 交付物：`lib/libmathic.a` 为 Release 产物（aarch64 ELF64，无宿主路径泄漏）。
- 双口径统计：`source_declared_total=14`、`configured_executable_total=14`、
  `executed_passed_total=14` → 14/14 = 100%（全量通过率 == 可执行集合通过率）。

## 适用边界 / 反例

- 适用：测试框架头/模板密集 → gtest_discover_tests 展开的测试目标，在内存受限
  worker 上 Release 编译峰值超限。
- 不适用：测试目标是交付物本身（不能降优化）；优化等级差异会改变断言语义
  （本轮未观察到）；真实编译错误（语法/链接）不能被 -O1 掩盖。
- 同类家族：baloo/6.28.0 的 `-j1`、E2168 的迭代降级——本条是「仅封顶非交付
  目标优化等级」的具体对策，与它们可组合。

## 查重

- 四范围（正式 E 条目 / doc/ / graph / drafts）均未命中该具体对策；
  memtailor-1.4 草稿覆盖的是 CMake 作用域/安装/GTest 命名三个根因（mathic 1.5
  的 C1/C2/C3 与其完全重复，已复用），本条（C4）为新增差异。
- 七轴：exact_duplicate=否；causal_duplicate=否；trigger_overlap=部分；
  solution_overlap=部分（与 -j1 同族但独立）；combination_novelty=是；
  boundary_novelty=是；test_migration_novelty=是。
- 关系：similar_to=[DRAFT-memtailor-1.4-subdir-ctest-false-pass-install-static-and-conan-gtest-targets,
  DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent]；conflicts_with=无；
  caused_by=无直接前驱；prerequisite_of=无。