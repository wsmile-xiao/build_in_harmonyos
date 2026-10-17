# E257 — Header-only CMake 包的 CTest 目标数与逻辑用例数分层核对

## 错误特征
适配报告把 `ctest -N` 的 1 个 CTest target 写成逻辑调用数，或把
`test_package` 的消费者断言并入上游测试通过率；也可能只报告消费者测试通过，
却没有运行上游唯一的 CTest 驱动。

## 触发条件
- 构建系统：CMake/CTest
- 阶段：测试清单核对、Conan 打包和消费者验证
- 对象：header-only `INTERFACE` 库，或 `main()` 内聚合多个逻辑测试的数据驱动测试

## 根因分析
CTest 的统计单位是由 `add_test()` 注册的可执行入口；一个入口的 `main()` 可以
顺序调用很多测试函数、条件检查和真实数据回归。反过来，Conan `test_package`
验证的是安装包的消费者视角，不能证明上游回归已经运行。两者若混成一个数字，
就会出现“target 数、逻辑用例数、消费者断言数”口径错位。

## 解决方案

### 推荐方案
1. 运行 `ctest --test-dir <build> -N`，记录 CTest target 数。
2. 阅读每个上游测试驱动的 `main()`，统计实际逻辑测试调用；若有数据目录循环，
   单独记录数据条目数，不能把它们冒充 CTest target。
3. 运行完整上游测试并单独记录退出码/输出；再运行 `test_package`，只把消费者
   断言记入消费者验证。
4. 对 header-only CMake 包，额外验证安装后的 `find_package(CONFIG)` 和上游
   导出的 INTERFACE target，确保不是空壳 include 测试。

### 禁止做法
- ❌ 用 `test_package` 通过替代上游测试通过率。
- ❌ 将 1 个 CTest target 宣称为 105 个独立 CTest target，或将上游驱动的
  105 个展开调度点写成适配后新增测试。
- ❌ 只编译空的头文件 include，不调用实际 API。

## 验证
```bash
ctest --test-dir <build> -N
ctest --test-dir <build> --output-on-failure
conan test <src>/test_package <package-reference>
```

## EWAHBoolArray 0.8.0 证据

上游 `tests/CMakeLists.txt` 只注册 `unit` 这 1 个 CTest target；
`tests/unit.cpp` 的 `main()` 展开调用 105 个可失败测试点，归属 37 个逻辑测试族，
并遍历 207 组 bitmap dump 数据。上游驱动在 clang++ C++11 主机验证中退出码为 0，
输出 `Your code is ok.`。
适配新增的 `test_package/test.cpp` 是消费者测试，包含真实 `EWAHBoolArray` 和
`BoolArray` API，共 8 个运行时检查；它不计入上游 105 个展开调度点。

最终提交 `f08dfba7eeb91967cf22cb15d7136f13e850e352` 在 OHOS armv8/Release、Conan
2.29.1、CMake 4.1.2、clang 15.0.4 上强制重建并验证：上游 CTest `1/1` PASS，
消费者 CTest `1/1` PASS，Conan 命令退出码 0。

## 路径 B 价值与查重

本条目沉淀的是可跨库复用的“CTest target / 驱动逻辑用例 / 数据回归 / 消费者断言”
四层清单方法，适用于 header-only CMake/Conan 适配的 PR 模板和 CI 证据审计。
E292 已要求区分 CTest target 子集与完整测试，但不提供 header-only 包消费验证和
单一驱动内部逻辑计数的组合审计；E307 侧重 CMake 缺失时的直编回退；E301 单独
覆盖 `CMake.test`/`CMake.ctest` 参数路由，不在本文重复。本文的增量是把这些口径放进同一份适配清单，
并以 EWAHBoolArray 的真实 `1 / 105 / 37 / 207 / 8` 证据示范。

## 关联条目
- 相关：E292、E307、E301
