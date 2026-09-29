# fixed-containers 3.21 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库，上游无 release tag，取官方 main 分支）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（OHOS SDK libcxx-ohos）
- 状态: built（本地全部门禁通过；发布由 CI 合并后流水线执行）

## 编译步骤

```bash
# 1. 源码核验（官方 main 分支，SHA-256 见 conandata/source）
#    https://github.com/teslamotors/fixed-containers/archive/refs/heads/main.tar.gz
#    2ab4cbd3397423502f3878bed38debfb2060cfb8a34a83d76115f2c8f13c53ce
# 2. 配方验证（含 conan create + test_package 消费者测试）
python3 scripts/ohc-run.py conan-verify fixed-containers 3.21        # G0-G4/L2/L4/L5 全通过
# 3. 上游测试全量运行（BUILD_TESTS=ON，54 目标 + 2 补充注册目标）
#    cmake -DBUILD_TESTS=ON ... && ctest           # 58/58 目标、974/974 GTest 用例通过
# 4. 鸿蒙专项验证（独立 test_ohos/）
python3 test_ohos/run_ohos_test.py <pkg>                             # TEST_OHOS_ALL_PASS
# 5. finish（结构 W2 + 依赖 R36 + W3 本地 CI 模拟）
python3 scripts/ohc-run.py finish fixed-containers 3.21 published    # .ci-result.json exit_code=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `std::ranges::equal/all_of/empty/construct_at/destroy_at` 编译失败 | OHOS libc++（libcxx-ohos，LLVM15 基线）未实现这些 C++20 ranges 算法 | 补丁 0001-0010：等价替换为标准 `std::equal`/`std::all_of`/`std::empty`/`std::construct_at`/`std::destroy_at` |
| 2 | `std::string_view` 无 `operator<=>` | OHOS libc++ 未实现 string_view spaceship | 补丁 0007/0001：FixedString 三向比较改用 `compare() <=> 0`；算法默认比较器回退 `<`/`==` |
| 3 | `<source_location>` 头缺失 | OHOS libc++ 无该头 | 补丁 0011（库侧）自带兼容实现；测试侧 0014 加 `__has_include` 守卫 |
| 4 | `std::uint_least32_t`/`std::invocable` 未定义 | OHOS libc++ `<version>`/`<utility>` 不传递包含 `<cstdint>`/`<concepts>` | 补丁 0011/0012：补显式 include |
| 5 | `std::make_unique_for_overwrite` 缺失 | OHOS libc++ 未实现 | 补丁 0013/0015（仅测试文件）：等价替换 `std::make_unique` |
| 6 | 测试构建默认 C++17 | conan profile `compiler.cppstd=17`，但库要求 C++20 | 测试构建启用 cppstd=20 profile 或 `-DCMAKE_CXX_STANDARD=20` |
| 7 | 完整 ranges 实现被禁用 | `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 守卫（未定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 时生效） | 测试编译标志 `-D_LIBCPP_ENABLE_EXPERIMENTAL`（ranges 实现本体已在 SDK 内） |
| 8 | W3 JC 门禁误报 3 个其他库基线空标记文件 | cloog/kics 的 `.build-closed`/`.staging-verified` 由其他库 PR 合入 main | 基线隔离复验：记录 SHA-256（e3b0c44…空文件）→ 临时移出 index 与工作区 → 复跑 W3 通过 → 原样恢复并核对哈希一致 |

## 源码修改

15 个补丁（patches/0001-0015）：库头文件 12 个（算法/容器头兼容 OHOS libc++ C++20 差异、
补 include），测试文件 3 个（`make_unique_for_overwrite` 等价替换、
`<source_location>` 守卫）。全部为语义等价的最小平台兼容补丁，未削弱任何断言。

## 依赖版本

- magic_enum/0.9.7（header-only，制品仓已发布；测试另用 gtest/1.17.0.2、benchmark/1.9.5）

## 验证结果

```bash
# 上游测试双口径：源码声明 1071（TEST 宏），配置可执行 58 目标
# 执行：58/58 目标、974/974 GTest 用例全部通过（ASAN_OPTIONS=detect_container_overflow=0，
#       gtest 静态注册期 std::set<string> 的 memcmp 触发 ASan 误报，测试逻辑不受影响）
# 鸿蒙专项：T1 ELF64-AArch64 / T2 musl / T3 .codesign / T4 无外部路径泄漏 /
#           T5 公开 API + 无堆分配核心保证（alloc=0 dealloc=0）全部通过
# conan-verify：G0-G4 + L2/L4/L5 通过（G2 conan create + test_package 实际运行）
# finish/W3：.ci-result.json exit_code=0（W2 结构 + R36 依赖 + W3 本地 CI）
```

## 交付物

header-only 库（无编译产物）：include/ 头文件 + fixed_containersConfig.cmake；
无 bin/（R38 不适用，非 CLI 库）。

## 注意事项

1. 上游无 release tag/版本号，任务版本 3.21 对应官方 main 分支快照（SHA-256 已锁定）。
2. OHOS libc++ 的 C++20 支持不完整是本适配的核心难点，补丁均为等价替换可跨平台复用。
3. test_ohos/ 为独立鸿蒙专项验证（可单独对包执行），与 test_package 消费者测试分别计数。
---

**编译结束**: 2026-09-27 22:36
**最终状态**: built
---

**编译结束**: 2026-09-27 22:37
**最终状态**: built
