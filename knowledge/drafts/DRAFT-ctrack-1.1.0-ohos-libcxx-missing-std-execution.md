# DRAFT-ctrack-1.1.0-ohos-libcxx-missing-std-execution：OHOS libc++ 缺失 `<execution>`/`std::execution`，C++17 header-only 库需经 `cpp_info.defines` 传播上游官方禁用宏

> Contributor: pc7-10 | Status: Draft | Updated: 2026-09-20
> Source: ctrack 1.1.0 适配（第一轮，Path B 知识库扩展）
> 对应：`knowledge/drafts/DRAFT-ctrack-1.1.0-ohos-libcxx-missing-std-execution.kv`

## 现象

C++17 单头（header-only）库 `ctrack.hpp`（ctrack 1.1.0）在 OHOS 上被
消费者直接 include 编译时，编译器报：

```console
no member named 'execution' in namespace 'std'; did you mean 'exception'?
    constexpr auto execution_policy = std::execution::par_unseq;
```

头文件第一处 `std::execution` 失败后错误级联蔓延：同一头文件内后续模板
（`sum_field` 中 `std::transform_reduce` 的 `OPT_EXEC_POLICY` 实参、
`sum_squared_field` 等）全部跟着 "candidate template ignored: substitution
failure"，同一份源码在原生 Linux libstdc++/macOS/Windows MSVC 上正常。

## 根因

OHOS SDK（`ohos-sdk_26.0.0.18`）自带的 `libcxx-ohos` 不提供 `<execution>`
头文件与 `std::execution` 并行执行策略（par / par_unseq）。上游 ctrack 在
未定义 `CTRACK_DISABLE_EXECUTION_POLICY` 时无条件：

```cpp
#ifndef CTRACK_DISABLE_EXECUTION_POLICY
#include <execution>
#endif
...
constexpr auto execution_policy = std::execution::par_unseq;
```

**关键**：上游 CMakeLists 自己就做了这个降级——`find_package(TBB QUIET)`
未命中时 `set(DISABLE_PAR ON)` 并 `target_compile_definitions(ctrack
INTERFACE CTRACK_DISABLE_EXECUTION_POLICY)`。OHOS 无 TBB 预编译包，
`CTRACK_DISABLE_EXECUTION_POLICY` 就是上游官方设计的禁用路径，不该改上游
源码硬删并行代码。

## 方案

**主方案（不侵入上游源码）**：conanfile.py 的 `package_info()` 把官方禁用宏
作为 INTERFACE 编译定义传播给所有消费者：

```python
def package_info(self):
    ...
    self.cpp_info.defines = ["CTRACK_DISABLE_EXECUTION_POLICY"]
```

- header-only 库没有编译产物，宏只能靠 `cpp_info.defines` 传播；
  CMakeDeps 自动写入传递依赖的 `INTERFACE_COMPILE_DEFINITIONS`，
  test_package 与下游消费者无需显式 `-D`。
- 本地验证：`clang++ -std=c++17 -O2 -DCTRACK_DISABLE_EXECUTION_POLICY
  -I$TEST_PREFIX/include consumer.cpp -pthread && ./a.out` → rc=0。

**备选（上游无官方宏时）**：最小补丁在头文件加 `#ifndef` 守卫包住
`<execution>`/`std::execution` 用法，patch_type: build-fix。

**禁止**：伪造 `std::execution` 命名空间、强塞 `-Dexecution`、硬拉 TBB
工具链依赖（R36 门禁风险）。

## 验证

| 项 | 结果 |
|---|---|
| 上游测试（doctest 69 个 TEST_CASE） | 69/69 (100%) 全量通过 |
| test_package.cpp（R34 消费者） | 编译运行 rc=0 |
| consumer_app.cpp（消费者用例） | 编译运行 rc=0，公开 API 条目验证 |
| ohos_special_test.cpp（鸿蒙专项） | 编译运行 rc=0，4 线程隔离验证 |
| conan create（G2 干净构建） | PASS（宏经 cpp_info.defines 自动注入） |

## 适用范围与边界

- **适用**：依赖 `std::execution` 并行策略的 C++17+ header-only / 头部内联库
  在 OHOS（libcxx-ohos）下裸 include 即命中。典型：profiling、benchmark、
  数值算法单头库。
- **不适用**：仅使用 `<execution>` 的其它平台（Linux/macOS/Windows 原生
  libstdc++/MSVC 均提供）；库已自备跨平台守卫或不用并行策略的情况。

## 查重结论（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | 否 — 无任何既有条目精确覆盖 |
| causal_duplicate | 否 — E130 同为 libcxx-ohos 头文件缺口但根因是 C++11→17 标准版本，本条是 `<execution>` 头缺失 |
| trigger_overlap | 部分 — 与 E130（libcxx-ohos 编译失败）共享工具链触发面 |
| solution_overlap | 部分 — 与 E322（header-only 配方模式）同属配方编写面，但 E322 管 build 选项/package_id，本条管编译定义传播 |
| combination_novelty | 是 — std::execution 缺失 × cpp_info.defines 宏传播的组合无既有覆盖 |
| boundary_novelty | 是 — 明确了"上游官方禁用宏优先、禁止伪造/硬拉 TBB"边界 |
| test_migration_novelty | 否 — 无测试迁移成分 |

关系：`similar_to`: E130, E322；其余关系字段为空。

## 决定

`new_draft`（Path B）— 已验证、可跨库复用（任何依赖 std::execution 的
header-only 库），查重未命中或部分覆盖且存在新增差异，建立同 stem 的
.md/.kv 草稿对。
