# physunits-ct-cpp11 1.4.0 — 适配笔记

## 软件信息

- **名称**: physunits-ct-cpp11（上游项目 PhysUnits-CT-Cpp11）
- **版本**: 1.4.0
- **源码**: https://github.com/martinmoene/PhysUnits-CT-Cpp11/archive/refs/tags/v1.4.0.tar.gz
- **上游提交**: c7d2c7c1b0d67c63f7a0f98160104bce9dd8ca99（v1.4.0）
- **SHA256**: 4d1f3a4901ef910ae492ed7c5719da0c68f4f3a8551cdfbc90e3ab8aa02ab882
- **构建系统**: CMake
- **许可证**: BSL-1.0

## 配方设计

- `package_type = "header-library"`，上游导出 `PhysUnits::PhysUnits` INTERFACE target。
- 无第三方 Conan 依赖，仅依赖 C++ 标准库。
- `package_info()` 不声明链接库，提供 `include/` 和 `PhysUnits::PhysUnits` CMake target。
- 无源码补丁；未修改上游测试。
- Conan 构建开启上游测试，关闭 examples。

## 测试证据

上游源码的 `test/physunits.t.cpp` 有 39 个 `CASE` 定义，其中 30 个是默认 CMake 测试实际注册并执行的命名用例；7 个编译期专用块和 2 个 `#if 0` 块不在默认测试路径。四个 C++11/14/17/20 runner 各执行这 30 个用例，设备实测为 120/120 次执行通过；每个 runner 输出 456 条 `passed:` 断言。

设备端命令：

```text
cmake -S /storage/Users/currentUser/builds/physunits-1.4.0.work -B /storage/Users/currentUser/tmp/physunits-ct-cpp11-1.4.0/upstream-build -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ -DPHYS_UNITS_OPT_BUILD_TESTS=ON -DPHYS_UNITS_OPT_BUILD_EXAMPLES=OFF
make -C /storage/Users/currentUser/tmp/physunits-ct-cpp11-1.4.0/upstream-build -j1
ctest --test-dir /storage/Users/currentUser/tmp/physunits-ct-cpp11-1.4.0/upstream-build --output-on-failure --no-compress-output
```

结果：CTest 4/4 通过，30/30 distinct cases 通过，120/120 runner executions 通过；没有上游失败或跳过。

首次 `make -j2` 在鸿蒙设备的 HMFS 工作区触发 `make: jobserver mkfifo: ... Operation not permitted`，这是并发 jobserver FIFO 权限限制，不是源码或测试失败。按工作区规则降为 `make -j1` 后完整构建和测试通过。

Conan `test_package` 增加 1 个 C++11 consumer case，实际包含 `phys/units/io.hpp`、使用单位字面量、量纲运算和 IO API，共 6 项显式检查，设备端结果为 1/1 通过。

## 知识库路径判断

本次为路径 A（基础适配）：上游 CMake、头文件和测试均无需 OHOS 源码补丁；仅按现有 OHOS Conan/CMake 规则完成配方和 consumer 验证。使用了 CMake/header-only 构建规则、R32 OHOS settings 规则、R34 实际 API consumer test 规则和 R26 无库链接规则。未形成可独立推广的路径 B 平台修复结论。
