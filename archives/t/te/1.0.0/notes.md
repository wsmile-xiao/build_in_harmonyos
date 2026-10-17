# te 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake (header-only, 无编译产物)
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, target aarch64-linux-ohos)
- 状态: built

## 编译步骤

te 是 header-only 库（boost-ext/te, C++17 type erasure），全部 API 在
`include/boost/te.hpp`（600 行）。无 configure/编译步骤；使用官方 tag
v1.0.0 源码包，配方为 header-only 变体：仅安装头文件 + test_package
实际包含并使用头文件。

上游测试与示例用 CMake 构建验证：

```bash
clang++ -std=c++17 -Wall -Wextra -Werror -pedantic -pedantic-errors \
  -Wno-delete-non-abstract-non-virtual-dtor -Iinclude -Itest test/te.cpp -o te_tests
./te_tests   # exit 0 — 26/26（C++17 实例化集；源码声明 28，其中 2 个 concepts 用例
             # 受 #if __cpp_concepts 守卫，cppstd=17 不实例化；C++20 下 28/28 全过）
# 13 个 example/*.cpp 全部编译并运行通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `test/te.cpp` 用 `-Werror` 编译报 `-Wdelete-non-abstract-non-virtual-dtor`：libcxx-ohos 的 `std::vector<DrawableMutable>` 实例化触发 | OHOS SDK 的 libc++ 对"有虚函数但非虚析构"的 poly 包装类型在 allocator 内部实例化时告警，属于标准库实现差异，非 te 源码问题 | 增加 `-Wno-delete-non-abstract-non-virtual-dtor` 抑制该标准库内部告警；te 库头文件本身无告警 |

## 依赖版本

无第三方依赖（header-only，仅依赖 C++17 标准库）。

## 验证结果

```bash
./te_tests          # exit 0 — 26/26（C++17 实例化集；源码声明 28，2 个 concepts 守卫用例不实例化）
./te_tests_cpp20    # exit 0 — 28/28（C++20 全集）
13 examples 全部运行 exit 0
test_package test_te + ohos_special_test 实际调用 te::poly/Drawable 类型擦除，断言通过
```

## 注意事项

- te 是纯 header-only 库，`package_id` 清空（跨配置单包）；`cpp_info.libdirs/bindirs` 置空。
- 上游自带 conanfile.py 与本配方行为一致（均只分发 include/*.hpp）。
---

**编译结束**: 2026-09-19 22:34
**最终状态**: built
