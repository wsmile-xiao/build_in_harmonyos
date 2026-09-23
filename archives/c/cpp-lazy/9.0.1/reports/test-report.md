# cpp-lazy 9.0.1 测试报告

## 结论

HarmonyOS/OHOS AArch64、Clang 15、C++17 配置下全部测试通过。

| 测试层级 | 总数 | 通过 | 失败 | 跳过 |
|----------|-----:|-----:|-----:|-----:|
| 上游 doctest 用例 | 290 | 290 | 0 | 0 |
| 上游 doctest 断言 | 12348 | 12348 | 0 | 0 |
| Conan test_package 程序 | 1 | 1 | 0 | 0 |
| test_package 运行时检查 | 12 | 12 | 0 | 0 |
| 上游示例编译目标 | 48 | 48 | 0 | 0 |

## 上游测试

- 测试目录：`tests/`
- 测试源文件：47 个 `.cpp`
- 构建产物：`tests`（一个 CTest 目标）
- 运行结果：290/290 test cases、12348/12348 assertions，状态 `SUCCESS`。
- 静态清点：291 个 `TEST_CASE` 声明；其中 `tests/string_view.cpp` 的 1 项回退实现测试由上游 `#if !defined(LZ_HAS_STRING_VIEW)` 守卫，C++17 提供 `std::string_view` 时按设计不注册；适用用例 290/290 全部通过。
- 适配仅将 doctest 获取从 FetchContent 改为赛事 Conan 远端的
  `doctest/2.4.11`；测试源码、注册、断言和预期结果均未改动。

## 消费者测试

`test_package` 通过 `find_package(cpp-lazy 9.0.1 CONFIG REQUIRED)` 和
`cpp-lazy::cpp-lazy` 消费安装产物，运行验证 map、filter、管道组合、to、range、
accumulate、contains、zip、format 和 distance，共 12/12 项检查通过。

## 补充验证

- 上游 `examples/CMakeLists.txt` 的 48 个示例目标全部使用 OHOS AArch64 工具链编译通过。
- 独立使用安装产物自带的 `cpp-lazyConfig.cmake` 进行版本化 CMake 查找、编译与 QEMU 运行，12/12 项检查通过。
- `fmt/12.2.0` 使用制品仓已发布的 `shared=True` OHOS 包；冷缓存安装不触发源码构建。
- `conan-verify`：G0、G1、G2、G3、G4、L2、L4、L5 全部 PASS。
- W3 本地 CI：总体 100% 通过；L0、L1、L4、L5 通过，header-only 库无 `bin/`，L2 按规范不适用。
