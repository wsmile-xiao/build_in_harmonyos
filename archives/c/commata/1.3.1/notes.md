# commata 1.3.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK libc++)
- 状态: built

## 编译步骤

1. init-build 下载官方 tag v1.3.1 (commit 368968edcfc443c85db15c144365be2f7ce4be8b)
2. 构建上游测试:
   ```bash
   cmake -S . -B build -DCOMMATA_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Release
   cmake --build build -j4
   ./build/src_test/test_commata   # 668/668 PASSED
   ```
3. conan-init 生成配方, conan-verify 验证, finish 收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 Fancy 用例编译失败: `std::basic_string<..., tracking_allocator<fancy_allocator<wchar_t>>>::__rep` 默认构造被隐式删除 | OHOS 工具链 libc++ 的 std::basic_string 内部 SSO union `__rep` 无用户默认构造; 当 allocator 的 pointer 类型为 fancy_ptr(非平凡默认构造) 时 `__rep` 默认构造被删除。libstdc++/MSVC 下可编译, libc++ 下不支持 fancy pointer 分配器 | 在 TestRecordExtractor.cpp 的 Fancy 用例中按 `_LIBCPP_VERSION` 条件编译: libc++ 下改用 `tracking_allocator<std::allocator<wchar_t>>` 保留 allocator 传播验证(total > 0), 其他工具链保留 fancy_allocator |
| 2 | 上游测试 TablePull Move 用例 4 个失败(CharsBufferSizes/TestTablePull/{0,1,2,3}.Move): 移动 table_pull 后 `*pull2()` 返回 NUL 数据 | libc++ SSO(小字符串优化)阈值 22 字符: 测试源串 19 字符走 SSO 内联缓冲, `owned_string_input` 移动后字符串数据地址改变, 而 `base_parser`/handler 数据队列持有指向旧缓冲的直读指针 → 悬空。上游 CI(libstdc++, SSO 阈值 15) 下 19 字符走堆分配, 移动转移堆指针地址不变, 故上游未暴露 | 修改 `include/commata/char_input.hpp` 中 `owned_string_input`: 内部字符串改用 `std::unique_ptr<...>` 堆间接层, 保证移动后 data() 地址稳定, 直读指针不失效。668/668 测试通过 |

## 源码修改

1. `include/commata/char_input.hpp`: owned_string_input 的 s_ 成员从 `std::basic_string<Ch,Tr,Allocator>` 改为 `std::unique_ptr<std::basic_string<Ch,Tr,Allocator>>`, 相应调整构造/移动/operator()/swap, 保证移动后字符数据地址稳定(libc++ SSO 兼容修复)。
2. `src_test/TestRecordExtractor.cpp`: Fancy 用例按 `_LIBCPP_VERSION` 条件编译, libc++ 下用 std::allocator 替代 fancy_allocator 保留 allocator 传播验证。

## 依赖版本

- 无第三方运行时依赖(header-only C++17 库)
- 测试依赖: googletest v1.14.0 (FetchContent, 仅测试构建)

## 验证结果

```bash
cd /storage/Users/currentUser/builds/commata-1.3.1.work
./build/src_test/test_commata
# [==========] 668 tests from 107 test suites ran.
# [  PASSED  ] 668 tests.
```

## 交付物

- header-only 库: include/commata/** (无编译产物)
- 无可执行文件 (R38: 不需要 commands.json)

## 注意事项

- OHOS 使用 libc++ (libcxx-ohos), SSO 阈值 22; 上游使用 libstdc++ SSO 阈值 15。两个适配点均为 libc++ 特有行为差异。
- make_char_input(std::basic_string&&) 路径 (owned_string_input) 现在引入一次堆分配; 语义与上游一致, 仅实现细节变化。
---

**编译结束**: 2026-09-03 07:31
**最终状态**: built
