# asyncpp 0.2.4 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，`cmake_minimum_required(3.25)`）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4（`aarch64-unknown-linux-ohos`），libc++ **15004**
  （OHOS SDK 26.0.0.18）
- Conan 2.29.1；profile `ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 /
  compiler=clang 15 / libc++ / **compiler.cppstd=17**）
- CMake 4.1.2；测试框架 Catch2 3.8.1（ohpcd 制品仓）
- 状态: built（设备端原生构建 + 上游 154 用例 + 消费者 25 断言全绿）

## 编译步骤

1. 下载官方 tag tarball 并校验（与 conan-center-index 的 recipes/asyncpp/all
   同源，见 conandata.yml 头注）：
   ```bash
   curl -sSL -o v0.2.4.tar.gz https://github.com/petiaccja/asyncpp/archive/refs/tags/v0.2.4.tar.gz
   sha256sum v0.2.4.tar.gz   # 58138ff5801d3a547eaad9adc2c30fe7a0d506c0e41dc56071ceaad5747210b5
   ```
2. 原生手工构建（Step 2，沙箱 `HOME=$TASK_DIR/test-home`）：
   ```bash
   cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
     -DCMAKE_CXX_STANDARD=20 \
     -DCMAKE_CXX_FLAGS="-D_LIBCPP_ENABLE_EXPERIMENTAL" \
     -DCMAKE_EXE_LINKER_FLAGS="-lc++experimental" \
     -DASYNCPP_BUILD_TESTS=ON -DASYNCPP_BUILD_BENCHMARKS=OFF \
     -DCMAKE_PREFIX_PATH=<catch2 包目录>
   cmake --build <build> -j4
   <build>/bin/test            # → All tests passed (N assertions in 154 test cases)
                               #   N=断言数，随并发调度逐轮波动（非稳定口径）；用例数恒 154
   ```
3. Conan 配方：`conan create` 从干净源码 `get + apply_conandata_patches` 起
   全量重建，`build()` 内直跑上游 Catch2 二进制（判据用 Catch2 汇总行，**不用
   ctest**——上游未调用 `enable_testing()`，ctest 恒以 `No tests were found!!!` +
   rc=0 假绿，device-facts §二.22）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `std::jthread` / `std::stop_token` 找不到（thread_pool、sleep、interleaver） | OHOS libc++ 15004 未实现 P0660（libc++ 至 LLVM 17 才提供） | 补丁 0005/0006/0007/0004：改 `std::thread` + `std::atomic<bool>` 停止标志 + 析构显式 `join()`，与 jthread「析构 request_stop + join」语义等价 |
| 2 | `std::chrono::clock_cast` 找不到（sleep.hpp） | libc++ 15004 未实现 clock_cast | 补丁 0003：同钟恒等返回，异钟 `clock_type::now() + (tp - Clock::now())` 相对时刻换算 |
| 3 | `no matching constructor for initialization of …`（shared_mutex 派生类、thread_pool::pack、`swarm_state(vec)`、`mtx_scope_clear guard(mtx)` 等 4 类形态） | **clang 15 不支持 C++20 括号聚合初始化（P0960，clang 16 起支持）** | 补丁 0002/0007/0004/0008-0010：基类与成员聚合初始化改花括号；测试辅助 RAII 结构与 `swarm_state` 补显式构造函数（**用例与断言零改动**） |
| 4 | `swarm_state` 的默认 `operator<=>` 被隐式删除 ⇒ `std::map<swarm_state, …>` 的 `std::less` 失效 | libc++ 15004 的 `std::vector` **没有 `operator<=>`** | 补丁 0004：`swarm_state` 改手写逐元素字典序 `operator<=>`（与默认实现等价）+ `operator==`（clang 15 只对**默认成员** `<=>` 做 `==` 重写，用户提供的 `operator<=>` 不参与重写） |
| 5 | `std::ranges::all_of/sort/unique/transform`、`std::views::filter`、`std::format` 全部 `no member named …` | libc++ 15004 把这些**默认关掉**，需 `_LIBCPP_ENABLE_EXPERIMENTAL`；`std::format` 运行时符号在 `libc++experimental.a` | 补丁 0001 新增 `ASYNCPP_LIBCXX_EXPERIMENTAL` 选项（默认 OFF），配方在 OHOS 上开启；`package_info()` 在 OHOS 追加 `system_libs=["c++experimental"]`（libpqxx 8.0.1、ladybug 0.18.2 同口径） |
| 6 | OHOS profile 钉 `compiler.cppstd=17`，而 asyncpp 必须 C++20（协程/concepts） | 共享 profile 为生态统一压低 | `generate()` 覆盖 CMakeToolchain `cppstd` 块为 20；`validate()` 只在 profile **显式高于 20** 时才拒绝（libpqxx 8.0.1 同口径） |
| 7 | `test/test_stream.cpp` 的 `#include <testing/interleaver.hpp>` 与上游 benchmark 需要 Celero | 上游 CMake 同时传入 `-I…/include/asyncpp/..` 与 `-I…/include/asyncpp`；Celero 在 ohpcd 缺档 | 前者**无需改动**（实测可解析，`flags.make` 两行 `-I` 为证）；后者按 W0「可选依赖缺省禁用」关 `ASYNCPP_BUILD_BENCHMARKS` |
| 8 | `std::format` 链接报 `undefined symbol: typeinfo for std::__n1::format_error` | OHOS 共享 libc++ 不含 format 运行时 | `-lc++experimental`（见 #5），已由消费者测试的 `testing::path::dump()` 实际拉链验证 |

## 源码修改

补丁 `patches/0001`–`0010`（逐条 `patch_description` 见 conandata.yml），按文件切分、
`refresh-patch --auto` 生成、每个补丁均通过 `patch --dry-run -p1` 校验：

| 补丁 | 文件 | 类别 |
|---|---|---|
| 0001 | `CMakeLists.txt` | 新增 `ASYNCPP_LIBCXX_EXPERIMENTAL` 选项（默认 OFF） |
| 0002 | `include/asyncpp/shared_mutex.hpp` | P0960：基类聚合初始化改花括号 ×2 |
| 0003 | `include/asyncpp/sleep.hpp` | 无 `clock_cast` → 同钟恒等 / 异钟相对换算 |
| 0004 | `include/asyncpp/testing/interleaver.hpp` | 无 `vector<=>` → 手写 `swarm_state` 比较 + 构造函数；`THREAD` 宏花括号；`jthread/stop_token` → `std::thread` |
| 0005 | `include/asyncpp/thread_pool.hpp` | `std::jthread` → `std::thread` |
| 0006 | `src/sleep.cpp` | `jthread/stop_token` → `std::thread` + `atomic<bool>` 停止标志 |
| 0007 | `src/thread_pool.cpp` | P0960 花括号 + `jthread` → `std::thread` + 析构 join |
| 0008–0010 | `test/test_{mutex,semaphore,shared_mutex}.cpp` | 测试**辅助 RAII 结构**补显式构造函数（P0960）；**用例与断言零改动** |

改写原则：只做「平台可移植性等价改写」，不改算法语义、不删用例、不改断言。

## 依赖版本

| 依赖 | 版本 | 类型 | 状态 |
|---|---|---|---|
| catch2 | 3.8.1 | test_requires（仅上游单测） | ✅ ohpcd 制品仓在档 |
| Celero | — | 上游 benchmark 可选依赖 | 缺档 → 关闭 `ASYNCPP_BUILD_BENCHMARKS`（不阻断） |
| pthreads | 系统内置 | 运行期 | ✅ OHOS 内置 |

**包本身 0 运行期依赖**（与任务卡一致）。

## 验证结果

```bash
# 上游测试（沙箱 HOME）
HOME=$TASK_DIR/test-home <build>/bin/test
→ All tests passed (N assertions in 154 test cases)   rc=0   （N 逐轮波动，用例数恒 154）

# 消费者测试（25 条运行期断言）
asyncpp consumer checks: 25 run, 0 failed               rc=0
```

- 上游：17 个测试翻译单元、**154 个注册用例**、断言数运行期自报且**随并发调度逐轮波动（非稳定口径）**，逐轮数值只记 `reports/test-report.md`；**PASS 154 / FAIL 0 / SKIP 0 / NOT_RUN 0**。
- 消费者：23 个公开头单 TU 自包含 + 25 条断言全过（含 `testing::path::dump()` 链接校验）。
- 详细两表与四口径清点见 `reports/test-report.md`。

## 注意事项

- 上游 `test/` 的三处修改仅是**测试辅助结构补构造函数**（P0960 语法形态问题），
  不改任何 `TEST_CASE`/`SECTION`/断言；PR 正文「上游测试用例修改说明」按「是」如实登记。
- benchmark/ 未构建（Celero 缺档），不属测试用例，不进上游分母。
- 上游 CMake 无 `enable_testing()`，**ctest 空跑 rc=0 属假绿**，任何判绿都必须读
  Catch2 二进制的汇总行。
