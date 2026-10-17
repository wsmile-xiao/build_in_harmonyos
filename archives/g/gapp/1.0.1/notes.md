# gapp 1.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++（OHOS SDK 26.0.0.18 自带 libc++ 15.0.4）
- 状态: built
- 目标: OpenHarmony PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）

## 编译步骤

```bash
# 配方（archives/g/gapp/1.0.1/conanfile.py）
conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
# 内部：get(官方 tarball) → apply_conandata_patches（3 个 portability 补丁）
#       → cmake -DGAPP_BUILD_TESTS=OFF -DGAPP_BUILD_BENCHMARKS=OFF
#                -DGAPP_BUILD_EXAMPLES=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON
#       → cmake --build → cmake install → test_package（15 条消费者断言）

# 上游测试（不在配方内，需 Catch2，沙箱 HOME 下单独跑）
cmake -S . -B build-tests -DCMAKE_BUILD_TYPE=Release -DGAPP_BUILD_TESTS=ON \
      -DCMAKE_PREFIX_PATH=<catch2/3.16.0 包目录>       # catch2 二进制取自 ohpcd 远端
cmake --build build-tests -j4
HOME="$TASK_DIR/test-home" ctest --test-dir build-tests --output-on-failure   # 446/446
HOME="$TASK_DIR/test-home" ./build/integration_tests                          # exit 0
HOME="$TASK_DIR/test-home" ./build/reproducibility_test                       # exit 0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `no member named 'atomic_ref' in namespace 'std'`（9 处） | OHOS SDK 的 libc++ 15.0.4 未实现 C++20 P0019R4 `std::atomic_ref`（上游 libc++ 16 才落地），`__cpp_lib_atomic_ref` 未定义 | 新增 `src/utility/cpp20_compat.hpp`：以标准特性宏守卫的最小 `atomic_ref`，操作逐项映射 `__atomic_*` 内建（`std::memory_order` 枚举值与 `__ATOMIC_*` 一致，直传），宏存在时整段不声明 |
| 2 | `no member named 'jthread' in namespace 'std'` | libc++ 15 未实现 C++20 `std::jthread`（`__cpp_lib_jthread` 未定义） | 同一兼容头：`jthread` 包装 `std::thread`，析构 join（上游只依赖"析构即 join"语义，未用 stop token） |
| 3 | `no member named 'lexicographical_compare_three_way' in namespace 'std'` | libc++ 15 未实现该 C++20 算法 | 同一兼容头：等价实现（返回 `weak_ordering`），受 `__cpp_lib_three_way_comparison` 守卫 |
| 4 | `no member named 'sort'/'find_if'/'is_sorted'/'all_of'/'equal' in namespace 'std::ranges'` | 该 libc++ 为裁剪版，`<algorithm>` 只提供迭代器对版本，`__cpp_lib_ranges` 未定义 | 同一兼容头：5 个 ranges 重载委托经典迭代器算法，投影经 `std::invoke` 应用，受 `__cpp_lib_ranges` 守卫 |
| 5 | `no member named 'fetch_add' in 'std::atomic<double>'` | 浮点原子 RMW（C++20）libc++ 15 未实现 | `pop_stats.cpp` 改为 relaxed CAS 累加环（语义等价、全平台可编译，无需特性宏） |
| 6 | 上游测试需 `find_package(Catch2 3)` | 测试专用依赖，不属于打包面 | 配方 `GAPP_BUILD_TESTS=OFF`；测试用 ohpcd 远端 `catch2/3.16.0` 二进制单独构建运行 |

## 源码修改

- `patches/0001-src-metrics-pop_stats.cpp.patch`：浮点 `fetch_add` → relaxed CAS 环（portability，无平台宏）
- `patches/0002-src-utility-cpp20_compat.hpp.patch`：新增 C++20 兼容头（portability，**全部受标准特性测试宏守卫**，上游/桌面工具链上不生效）
- `patches/0003-src-utility-utility.hpp.patch`：在 `utility.hpp` 引入兼容头（库、上游测试、消费者三方在同一点看到补丁）

未修改任何上游测试用例；`test/benchmark/`（上游默认 `GAPP_BUILD_BENCHMARKS=OFF`，CI 不构建）中同款 `std::atomic<double>::fetch_add` 用法未纳入本轮构建面。

## 依赖版本

- 运行/编译依赖：无（0 依赖）
- 测试期（不入配方）：`catch2/3.16.0`（ohpcd 远端二进制）

## 验证结果

```bash
# 干净轮采信（见 reports/ 与 reports/conan-verify-report.md）
conan_verify_round.sh gapp 1.0.1 --repo $TARGET_REPO --task-dir $TASK_DIR   # rc=0

# 上游测试（沙箱 HOME）
ctest：100% tests passed, 0 tests failed out of 446        # 总耗时 42.42s
./build/integration_tests        # exit 0（51 个 "Function:" 场景结果打印完毕）
./build/reproducibility_test     # exit 0（integer-1==integer-2=11；multi-thread-1==multi-thread-2=-0.146872）
./build/rcu_test                 # 常驻压测无退出条件：Release 版 250s、-UNDEBUG 断言生效版 60s，
                                  # 均无断言失败/崩溃，人工终止（上游 CI 未注册该入口）

# 消费者
test_package：consumer assertions: 15/15
```

## 注意事项

- `manifest.yaml` 状态按 O5 口径写 `built`（合并 + CI release upload 确认前不写 `published`）。
- 上游仓库根自带 `conanfile.py`（作者自己的打包配方），本仓库配方按归档规范另写，两者互不引用。
