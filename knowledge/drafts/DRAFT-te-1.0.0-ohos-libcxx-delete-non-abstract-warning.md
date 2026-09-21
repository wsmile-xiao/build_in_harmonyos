# DRAFT-te-1.0.0-ohos-libcxx-delete-non-abstract-warning — OHOS libcxx 对擦除/包装类型容器化触发 -Wdelete-non-abstract-non-virtual-dtor

## 问题现象

te（boost-ext/te，C++17 单头文件类型擦除库）在 OHOS armv8 上按上游
CMakeLists 的严格模式编译上游测试时失败：

```
$ clang++ -std=c++17 -Wall -Wextra -Werror -pedantic -pedantic-errors \
    -Iinclude -Itest test/te.cpp -o te_tests
...libcxx-ohos/include/c++/v1/__memory/allocator.h:170:9:
error: destructor called on non-final 'DrawableMutable' that has virtual
functions but non-virtual destructor
[-Werror,-Wdelete-non-abstract-non-virtual-dtor]
    __p->~_Tp();
...test/te.cpp:855:34: note: std::vector<DrawableMutable> drawables_mut{b, c};
```

同样的告警在 `-Werror` 下从标准库头文件内部实例化冒出，变成整仓编译失败。

## 根因分析

1. te 的接口包装类型（test 中 `struct DrawableMutable : te::poly<DrawableMutable,
   te::non_owning_storage>`）含虚函数但无虚析构——这是类型擦除接口的正常形态
   （擦除的是 draw 调用，析构由存储策略管理）。
2. OHOS SDK 的 libcxx-ohos（clang 15）在标准库内部模板实例化时
   （`std::allocator<DrawableMutable>::destroy` /
   `std::__uninitialized_allocator_copy`，来自 `std::vector<DrawableMutable>`
   构造），对这类非 final、有虚函数无虚析构的类型触发
   `-Wdelete-non-abstract-non-virtual-dtor`。
3. 该告警发自标准库实现内部，不是 te 源码自身诊断；上游 CMakeLists 同时开启
   `-Werror -pedantic-errors`，告警转错误 → 编译失败。libstdc++ 同代码不告警，
   属标准库实现差异，非三方库缺陷。

## 方案

保留上游全部严格标志，仅对该标准库内部实例化告警做单项抑制
（不降级 -Wall/-Wextra/-Werror/-pedantic 任何其他检查）：

```bash
/data/service/hnp/bin/clang++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -pedantic-errors -Wno-delete-non-abstract-non-virtual-dtor \
  -Iinclude -Itest test/te.cpp -o te_tests
./te_tests   # exit 0，26/26 用例通过（C++17 实例化集；源码声明 28，2 个 concepts 守卫用例不实例化；C++20 下 28/28）
```

## 验证（te 1.0.0 本轮真实日志）

1. 加 `-Wno-delete-non-abstract-non-virtual-dtor` 后 test/te.cpp 编译通过（exit 0），
   运行 26/26 独立用例全部通过（C++17 实例化集，源码声明 28、2 个 concepts 守卫不实例化；
   另以 C++20 全集验证 28/28 通过，manual-te-build2.log）；
2. 13 个 example/*.cpp 同样编译（examples-build.log）并运行（exit 0）全部通过；
3. conan-verify G2（conan create 干净构建 + test_package 消费者）PASS。

## 适用范围与边界

- 适用：OHOS（aarch64-linux-ohos，clang 15 + libcxx-ohos）上以 -Werror /
  -pedantic-errors 严格模式编译、且将含虚函数无虚析构的擦除/包装类型放入标准
  容器（vector 等）的 C++ 库（类型擦除库、策略包装库、接口装箱库常见）。
- 边界：若告警发自**项目自身源码**（非标准库内部实例化），应修复源码
  （补虚析构或 final），不得用 -Wno-* 掩盖；仅标准库内部实例化产生的该告警
  才用单项抑制。
- 反例：不含擦除/包装类型容器化的库不会触发，无需加此标志。

## 查重（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | false（与既有 libcxx 缺失头/特性类条目不同源） |
| trigger_overlap | false |
| solution_overlap | partial（-Wno-* 抑制类方案与既有 flags 类条目相似） |
| combination_novelty | true |
| boundary_novelty | true（标准库内部实例化告警 + -Werror 严格模式） |
| test_migration_novelty | false |

- similar_to: E257, E307, E321, DRAFT-graaf-1.1.0-ohos-libcxx-std-ranges-missing, DRAFT-libfork-3.6.0-libcxx-missing-headers, DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental
- caused_by: [] / prerequisite_of: [] / conflicts_with: []
- 同源关系：本库与 main 既有归档 archives/b/boost-te（同一上游 boost-ext/te、
  同一 v1.0.0 tag、同一 sha256）为同源；K1/K2 陷阱（copy 相对路径、W3 full 模式
  基线噪声）已由 DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental
  覆盖，本草稿仅承载新增差异（libcxx 告警抑制）。
- 决定: `new_draft`（路径 B，与 te 归档进同一 PR）