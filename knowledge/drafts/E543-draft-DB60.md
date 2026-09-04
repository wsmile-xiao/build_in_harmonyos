# E543 — OHOS 缺少 Boost.Test 链接库时保留上游套件的 header-only 迁移与消费验证

## 错误特征

上游测试入口包含 `<boost/test/unit_test.hpp>`，但 OHOS 的 Boost 制品没有可用的
`libboost_unit_test_framework`，链接时出现 `undefined reference` 或组件库找不到。
不能因为测试框架链接失败就关闭整套上游测试并报告“通过”。

## 触发条件
- 构建系统: CMake/Conan 2
- 阶段: 编译、链接或测试
- 适用范围: OHOS 上游使用 Boost.Test 的 C++ header-only 或 CMake INTERFACE 库

## 根因分析

制品仓可能只提供 Boost 头文件，或只提供不匹配的 Boost 二进制组件；而上游的
`unit_test.hpp` 入口通常要求单独链接 `libboost_unit_test_framework`。对于只需
测试框架的 header-only 库，这不是被测库运行时依赖。若简单关闭测试，会丢失上游
算法和边界覆盖，且无法区分“测试未运行”和“测试通过”。

## 解决方案

### 推荐方案

1. 先确认 Boost 制品实际提供的头文件和 `libboost_unit_test_framework`，记录版本和
   包内容。
2. 通过 `patches/` 与 `conandata.yml` 对上游唯一测试入口改为
   `boost/test/included/unit_test.hpp`，不修改断言、不删除测试源文件。
3. 以 test-only `tool_requires` 提供 Boost 头文件，编译并运行上游全部测试翻译单元，
   记录 Boost.Test 运行时的真实 test-case 数和错误数。
4. 保持被测包的运行时依赖图为空（header-only），再用 `CMakeDeps`、CMake target
   和独立 `test_package` 调用真实 API，避免只验证源码目录头文件。

### 禁止做法
- ❌ 将 `BUILD_TESTING=OFF` 或静默 `skip upstream` 当作上游测试通过。
- ❌ 用 `tool_requires("cmake/...")` 掩盖设备工具链问题。
- ❌ 修改上游断言、删减测试源，或把测试框架误列为消费者运行时依赖。

## 验证
```bash
conan create <recipe> --profile:host=ohos-aarch64 \
  --profile:build=ohos-aarch64 --build=missing
grep -E "Running [0-9]+ test cases|No errors detected" <raw-log>
conan test test_package <package-reference>
```

array-hash 0.7.2 的 HarmonyOS aarch64 实证：上游五个测试源运行 `153/153`，输出
`*** No errors detected`；Conan `test_package` 构建并运行 `1/1`，消费者程序的
10 个 map/set 检查全部通过。该实例使用 `boost/1.90.0` 头文件和一个只改测试入口
的补丁，未给消费者引入 Boost 依赖。

## 关联条目
- 相关: E035（Boost header-only 安装）、E099（Boost.Build/b2 在 OHOS 上的边界）、
  E321（Conan2 header-only 配方迁移）。
- 差异: 本草稿专门记录“Boost.Test 链接库缺失时仍保留完整上游套件”的入口迁移、
  测试计数和独立消费验证组合。
