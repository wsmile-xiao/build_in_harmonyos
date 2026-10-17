# mp-units 2.5.0 适配笔记

## 基本信息

- 上游：https://github.com/mpusz/mp-units
- 版本：2.5.0
- 类型：C++20 header-only CMake 库
- 最终本地提交：`bfd32544796e92d8587a82f8790f6052bf1d03ec`
- 当前状态：`built`（Conan 包与消费者通过；上游 runtime 通过；static compile-only 受 OHOS libc++ 缺特性限制）

## 编译环境与配方

设备为 HarmonyOS PC arm64（Conan `os=OHOS`, `arch=armv8`），工具为
Clang/Clang++ 15.0.4、CMake 4.1.2、Conan 2.29.1。配方从官方 `v2.5.0`
tag tarball 获取源码，SHA256 为
`a6bd48bee699f11f0ed5b04b8c5006d15f76e6d898e058db3880554d2e47a400`。

`CMakeToolchain` 显式设置 `CMAKE_SYSTEM_NAME=OHOS`、
`CMAKE_SYSTEM_PROCESSOR=aarch64`，配置 `src/` 子项目，关闭 C++ modules、
`std::format` 和 GSL contracts；hosted 格式化由 `fmt/12.2.0` 提供。
`package_info()` 同步传播 mp-units 的 API 宏，避免 OHOS libc++ 暴露不完整
`<format>` 时错误选择标准库 format 后端。

## OHOS Clang 15 源码兼容补丁

设备构建实际需要并成功应用 `0002` 至 `0009` 共 8 个补丁，修复上游源码中
Clang 15 对 dependent type 标记、嵌套立即求值辅助函数以及 base-value helper
的兼容性问题。所有补丁均限定在源码层，未修改测试框架或基础设施。

此前的 Conan 消费者问题也已修复：测试包只保留手动 `CMakeDeps`，并显式把
消费者 C++ 标准设为 C++20；最终输出为 `mp-units OK: 120 km/h`。

## 上游测试统计与结果

上游 runtime 由 `catch_discover_tests()` 注册，设备 CTest 实际发现 25 个
cases。执行命令为：

```text
/data/service/hnp/bin/ctest --test-dir $HOME/tmp/import-deps-100-odd-mp-units-upstream-r4 --output-on-failure
```

结果为 `25/25` 通过，直接 Catch2 汇总为 `786 assertions in 25 test cases`。
上游 `test/static/` 另注册 2 个 compile-only library targets；执行
`unit_tests_static` 时，`quantity_test.cpp` 在第 364--369、469--470、
553--561、563、589--592 行的复数静态断言触发 20 个编译诊断并停止。
诊断明确指向 OHOS SDK 的
`.../libcxx-ohos/include/c++/v1/complex:548`：非成员
`operator+<float/double/long double>` 不是 `constexpr`，所以依赖这些运算的
上游常量表达式不能成立。这是已定位的 OHOS 缺特性，不把 static targets
写成通过，也不修改上游测试绕过它。

设备日志：

- Conan 包构建与消费者：`$HOME/tmp/import-deps-100-odd-mp-units-create-r9.log`
- 上游 runtime/static 构建：`$HOME/tmp/import-deps-100-odd-mp-units-upstream-r4.log`
- 上游 runtime CTest：`$HOME/tmp/import-deps-100-odd-mp-units-runtime-r4.log`

## 其他设备环境提示

Conan 和测试包构建中出现 `Problem parsing /proc/meminfo` 以及
`make: jobserver mkfifo ... Operation not permitted`，二者均未导致退出失败；
任务使用 `$HOME/tmp` 保存日志，未写设备 `/tmp`。

## 交付范围

本包只安装 header 和 INTERFACE target，不提供 CLI，因此没有
`commands.json`。交付包含 Conan 配方、官方源码校验、8 个 OHOS Clang 15
兼容补丁，以及带 MANIFEST 的 test_package。

本轮没有形成新的可跨库知识条目，不申报路径 B 知识库扩展。
