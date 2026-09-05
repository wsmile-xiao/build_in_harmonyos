# E321 草稿：无安装规则/无 CTest 条目的老 CMake 归档

## 错误特征

老项目在 CMake 4.1.2 上可能首先报：

```text
Compatibility with CMake < 3.5 has been removed from CMake.
```

即使配置和构建成功，项目也可能没有 `install()`、`enable_testing()` 或
`add_test()`。此时 `ctest --output-on-failure` 会输出 `No tests were found!!!`
并返回 0；如果项目还通过 `configure_file` 生成公共头，只复制源码目录会遗漏该头。

## 根因与边界

这是上游构建描述不完整和现代 CMake 兼容策略共同造成的适配问题，不是可以
通过伪造测试数量解决的测试缺失。E187 已覆盖低版本 `cmake_minimum_required`
的单独兼容问题，E301 已覆盖 Conan CMake 测试参数路由，E309 已覆盖生成公共
头遗漏；本草稿新增的是三者在“无 install/无 CTest 的 Conan 归档”中的收尾组合。

## 推荐方案

1. 使用 `CMakeToolchain` 的 `cache_variables` 注入
   `CMAKE_POLICY_VERSION_MINIMUM=3.5`，不修改上游源码。
2. 构建后直接运行 `ctest --output-on-failure`，如无测试用例就明确记录为
   “上游 CTest 0 项”，同时运行上游提供的可执行示例作为 smoke test。
3. 从源目录复制公共头，从构建目录复制生成的公共头，从源码复制许可证，
   从构建目录复制库；不要依赖不存在的 `cmake.install()` 规则。
4. 以真实消费者测试调用包内 API，并把上游 0 项与消费者断言数分开统计。

## 设备验证

`string_id` 2.0-3 在 HarmonyOS PC aarch64、Clang 15.0.4、CMake 4.1.2
上验证：加入 policy 变量后构建通过；上游 `ctest` 如实返回零用例；官方
example 运行成功；Conan `test_package` 调用数据库、字面量和计数生成器，
11 项断言全部通过。

```bash
cmake -S <src> -B <build> \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DFOONATHAN_STRING_ID_DATABASE=ON \
  -DFOONATHAN_STRING_ID_MULTITHREADED=ON
cmake --build <build> -- -j1
ctest --test-dir <build> --output-on-failure
conan create archives/s/string_id/2.0-3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 禁止做法

- 不要把 `No tests were found!!!` 统计为上游测试断言通过。
- 不要只调用 `cmake.install()` 并假定无 install 规则的项目会生成完整包。
- 不要把构建目录中的生成公共头遗漏在包外。

## 关联条目

- E187：CMake 4.x 与低版本 `cmake_minimum_required`。
- E301：Conan CMake `test`/`ctest` 参数语义。
- E309：构建生成公共头的打包闭包。
