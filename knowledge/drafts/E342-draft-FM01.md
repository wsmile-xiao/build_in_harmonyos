# E342 — CMake 默认 CTest 与 Makefile 穷举测试的清单盘点

## 错误特征

上游同时维护 CMake 和 Makefile 测试入口时，`ctest -N` 只显示 CMake 注册的
目标，容易被误写成完整断言数或完整测试套件。fastmod 0.1.0 的默认 CMake
清单只有 `moddivnbenchmark` 和 `modnbenchmark` 两项；`unit.c` 与
`cppincludetest2.cpp` 是 Makefile/opt-in 穷举程序，默认不在 CTest 清单中。

## 触发条件

- 构建系统：CMake + Makefile
- 阶段：测试清单盘点、Conan 配方固化、PR 测试规模说明

## 根因分析

`add_test()` 注册的是可执行测试目标，而不是源码中的断言数量。项目的
Makefile 可以额外构建 correctness/exhaustive 程序，但如果 CMake 没有注册它们，
默认 `ctest` 就不会运行；反过来，benchmark 程序也可能只测运行/性能而不比较
正确性。header-only 包没有链接库产物，因此还必须用真实 API 的消费者程序验证
安装头文件和 CMake target。

## 解决方案

### 推荐方案

1. 从 `tests/CMakeLists.txt` 统计 `add_test()` 的实际注册数。
2. 从 Makefile 和 opt-in CMake 选项补充“构建但未默认执行”的程序清单。
3. 在 Conan `build()` 中保留默认上游 CTest，并在 `MANIFEST.yml` 和 PR 正文中
   分开写默认 CTest、可选穷举程序和消费者测试的数量与状态。
4. 对 header-only 包用 `self.run()` 执行直接 include 头文件并断言 API 结果的
   `test_package`，不得只打印 OK。

### 禁止做法

- ❌ 把 `ctest -N` 的目标数写成断言数。
- ❌ 把默认未启用的 exhaustive 程序或 Makefile-only 程序写成已通过。
- ❌ 用不 include 被测头文件的空壳消费者测试代替 API 验证。

## 验证
```bash
ctest -N --test-dir <build>
rg -n 'add_test|FASTMOD_EXHAUSTIVE_TESTS|unit|cppincludetest2' \
  CMakeLists.txt tests/CMakeLists.txt Makefile
clang++ -std=c++11 -I <package>/include <consumer>.cpp -o <consumer> && <consumer>
```

## 关联条目

- 相关：E307（header-only 消费者测试）、E301（CMake/CTest 执行证据）、E308（测试源文件门禁）
