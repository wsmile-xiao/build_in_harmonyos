# DRAFT-mmap_allocator-3.1-libcxx-mmappable-vector：libc++ 下 mmap-backed vector 内部指针 API 适配

## 现象

mmap_allocator 3.1（上游 https://github.com/ekg/mmap_allocator，master
HEAD adbfbe165）在 HarmonyOS PC（OHOS，libc++）交叉编译 conan create 时：

1. 首次 build 阶段：`cmake_minimum_required(VERSION 3.1)` 被 CMake 4.x 拒绝
   （该点与 E103/E187 等价命中，走路径 A，见附录）；
2. test_package 编译通过后运行 `test_mmap_allocator` 直接 SIGABRT：
   `libc++abi: terminating due to uncaught exception ... Cannot stat file testfile`
   以及编译期 `redefinition of 'mmap_file_identifier'`。

## 根因

上游 `mmappable_vector.h` 直接操作 GNU libstdc++ 的私有内部指针：

```cpp
Base::_M_impl._M_finish = Base::_M_impl._M_start + n;   // _M_set_finish()
A *the_allocator = &Base::_M_get_Tp_allocator();        // 配置 allocator
Base::_M_deallocate(Base::_M_impl._M_start, n);        // munmap
```

OHOS 工具链默认 `-stdlib=libc++`（compiler.libcxx=libc++），libc++ 没有
`_M_impl`/`_M_finish`/`_M_get_Tp_allocator` 这些 GNU 内部成员，导致：

- 编译期：直接 include 与经 `mmap_allocator.h` 间接 include 同一无 guard
  头文件 `mmap_file_pool.h` → 类重复定义（上游头文件无 include guard）；
- 运行期：libc++ 路径下 `mmap_file(n)` 无法推进 finish 指针，vector 大小
  不被认可；且 allocator 缺 construct/destroy 适配时 resize 会按值写入
  mmap 后备存储。

## 方案

1. **mmappable_vector.h（libc++ 分支，`#if defined(_LIBCPP_VERSION)`）**：
   - `mmap_file(size_t n)`：`Base::reserve(n); Base::resize(n);`
     （libc++ 无公开 API 推进内部 end 指针，resize 配合 allocator 的
     无操作 construct 仅推进内部指针而不写 mmap 内存）；
   - 带文件名重载：构造已配置的 `mmappable_vector configured(...)` 后
     `Base::swap(configured)` 交换存储（libc++ 派生类无法访问内部
     allocator 引用）；
   - `munmap_file()`：`Base::clear(); Base::shrink_to_fit();`
     （经 allocator::deallocate 释放 mmap 映射）。
2. **mmap_allocator.h（libc++ 分支）**：补充无参 `construct(U*)`/`destroy(U*)`
   为 no-op（不写入 mmap 后备区域），带参 construct 走 placement new；
   声明 `propagate_on_container_swap/move_assignment/copy_assignment =
   std::true_type`（有状态 allocator 随容器 swap/move 转移文件配置）。
3. **mmap_file_pool.h**：补 include guard（`_MMAP_FILE_POOL_H`），消除
   `mmap_allocator.h` 与直接 include 双路径下的重复定义。
4. **test 消费者顺序**：文件池记账（`mmap_file_identifier` 构造）会对文件
   `stat()`，释放映射（munmap）必须在删除文件之前完成，否则
   `Cannot stat file ...` 异常在析构路径抛出。

## 验证

- conan create（ohos-aarch64 profile：os=OHOS, clang 15, libc++,
  cppstd=17, Release）：exit 0；test_package ctest 1/1 通过；
- 上游回归 test_mmap_allocator（native）：exit 0，全部断言通过；
- W3 本地 CI（finish build_and_test.sh）：`.ci-result.json` exit_code=0，
  log_sha256=512426c6f1d51cbc283ede5a0d43cb963b41f9889da9191014d985a7ac2935b1。

## 适用边界与反例

- 适用：OHOS/HarmonyOS 默认 libc++ 工具链上，任何派生或组合
  `std::vector` 且依赖 GNU 内部指针成员（`_M_*`）的自定义容器/分配器库；
  libc++ 版本无 `_M_get_Tp_allocator` 类内部 API 的平台。
- 反例：GNU libstdc++ 工具链（`-stdlib=libstdc++` 或默认）保留内部成员，
  无需该分支；纯 header-only 且不使用 vector 内部布局的库不受影响。
- 限制：`shrink_to_fit()` 是否真正释放取决于实现（libc++ 通常释放）；
  若容器有其他持有者/引用，`clear()+shrink_to_fit()` 的释放语义需逐库核验；
  不得用 `#ifdef __OHOS__` 覆盖 GNU 路径，应保留两套实现按 `_LIBCPP_VERSION`
  分支。

## 附录：路径 A 等价命中（不创建草稿）

CMake 4.x 拒绝 `cmake_minimum_required(VERSION 3.x<3.5)`：
等价命中 E103（rec_approach=bump-cmake-minimum-version，rec_command 即
sed 提升版本号）与 E187（fallback add-cmake-flag）。本库采用 E103 主方案
（conanfile `replace_in_file` 将 3.1 提升为 3.5），E187 的
`CMAKE_POLICY_VERSION_MINIMUM` 工具链变量实测对 CMake 4.1.2 无效，
仅 CLI `-D` 生效，故以 E103 为判定命中。逐字段适用性：error_signature
（匹配）、root_cause（匹配）、rec_approach（一致）、rec_command（一致）。

## 反例与限制补充

include guard 缺失（`mmap_file_pool.h`）属通用 C++ 卫生修复，无独立
知识价值（已有 E091/E119/E163 覆盖 kernel 头重定义类），不单列草稿。
