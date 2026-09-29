# DRAFT: stb 风格 single-file 头文件库 aarch64 支持（gb 0.8.7 实证）

> 状态：DRAFT — 待审核 promote。对应 .kv：`DRAFT-gb-0.8.7-single-file-header-aarch64-support.kv`

## 问题

stb 风格 single-file C/C++ 头文件库（gingerBill/gb 0.8.7 实证）在
aarch64（OHOS arm64 主架构）上编译消费者时报一串平台缺失错误：

```
gb.h:250:3: error: Unknown CPU Type                # CPU 检测块无 aarch64 分支
gb.h:4419:2: error: TODO(bill): Implement Atomics for this CPU
gb.h:4547/4559/4571/4583: error: Unknown architecture  # yield/mfence/sfence/lfence
gb.h:4760: error: Unsupported architecture for gb_thread_current_id()
ld.lld: error: undefined symbol: gb_rdtsc          # rdtsc 仅 x86/PPC 分支
```

## 根因

single-file 库的 CPU/平台检测与实现段只覆盖作者常用平台（x86/PPC/ARM32），
aarch64 落入 `#error` 或缺失定义；`GB_ARCH_64_BIT` 位宽检测遗漏
`__aarch64__`，64 位误判 32 位，连带原子/指针对齐全局假定出错。

## 方案（三补丁，按序应用）

1. **CPU 检测**：ARM 分支加 `__aarch64__`：
   `#elif defined(__arm__) || defined(__aarch64__)` → `GB_CPU_ARM=1`。
2. **实现段补齐**：
   - `GB_ARCH_64_BIT` 检测补 `__aarch64__`/`__arm64__`；
   - 32/64 原子操作用 GCC/Clang `__atomic_*` 内建
     （load/store/exchange/compare_exchange/fetch_add/and/or）；
   - fence：`gb_mfence = __sync_synchronize()`、`gb_sfence = dmb ishst`、
     `gb_lfence = dmb ishld`、`gb_yield_thread = 编译器优化屏障`；
   - `gb_thread_current_id = (u32)(uintptr_t)pthread_self()`。
3. **高精度计数器**：`gb_rdtsc` 用 `__asm__("mrs %0, cntvct_el0")`
   （ARM 通用计数器，单调递增）替代 x86 rdtsc。

**消费者约定**：stb 风格头文件库须在单个编译单元
`#define GB_IMPLEMENTATION` 后 include 才能实例化实现（gb.h 官方用法）。

## 验证（gb 0.8.7 实证）

- conan-verify：G1 配方完整性 / G0 预检 / G2 conan create（含 test_package
  编译+运行）/ G3 隔离 / G4 产物 / L2/L4/L5 全 PASS；
- OHOS 专项测试 `reports/ohos-test/ohos_test.c` 6 组断言 ALL PASS
  （GB_CPU_ARM / GB_ARCH_64_BIT / atomic32 fetch_add / atomic64 fetch_or /
  fence 执行 / rdtsc 单调性 + thread_id 非零）；
- test_package 消费者测试 4 组公开 API 断言 PASS
  （`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"passedCount":4}`）。

## 适用边界

- 适用：所有 stb 风格/single-file 头文件库在 aarch64（OHOS、其他 arm64
  Linux）下的 CPU 检测、原子、fence、高精度计数器、线程 ID 缺失场景；
  doctest/catch2/stb 系/gb 系同构问题可复用。
- 反例：头文件库只提供声明（实现由链接方提供）→ 无需实现段补丁；
  非 arm64 平台不适用；需 GCC/Clang `__atomic` 内建与 aarch64
  `dmb`/`mrs` 汇编（clang 15 已验证）。

## 查重与关系

- 四范围查重（index.tsv / doc / graph / drafts）：E257（G1 配方结构）、
  E100（CMake 平台禁 SIMD）、E030/E070（Autotools 位宽）、E006/E016
  （disable-asm）、DRAFT-9645（char 符号性）、DRAFT-EA（header-only 依赖
  传播）均不覆盖本模式（CPU 检测 + 实现段原子/fence/rdtsc 组合）。
- 七轴：exact/causal_duplicate=false；trigger/solution_overlap=false；
  combination/boundary/test_migration_novelty=true → `new_draft`。
- similar_to：E016、DRAFT-9645；caused_by：上游平台覆盖有限 + OHOS
  aarch64 主架构；prerequisite_of：gb 0.8.7 HarmonyOS 完整适配；
  conflicts_with：none。

## 产出位置

- 补丁：`archives/g/gb/0.8.7/patches/0001-aarch64-cpu-detection.patch`、
  `0002-aarch64-implementation.patch`、`0003-aarch64-rdtsc.patch`
- 证据：`archives/g/gb/0.8.7/reports/{knowledge-candidate-ledger,ohos-test/evidence,
  upstream-tests-ledger,baseline-isolation-audit}.md`