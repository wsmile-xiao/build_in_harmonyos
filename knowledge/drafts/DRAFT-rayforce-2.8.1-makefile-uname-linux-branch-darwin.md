# DRAFT: raw Makefile 的 `ifeq ($(UNAME_S),Linux)` 分支在 HarmonyOS 落入 macOS 专属链接参数

> 来源：rayforce 2.8.1 适配（纯 C17 零依赖引擎，任务 rayforce-2.8.1-r01-pc4-13，2026-09-21）
> 状态：草稿（随 PR 提交，定稿编号由主编确认）
> 关联台账：archives/r/rayforce/2.8.1/reports/knowledge-candidate-ledger.md

## 问题场景

raw GNU Makefile（非 autotools/CMake 生成）项目用 `uname -s` 做平台分支：

```make
ifeq ($(UNAME_S),Linux)
  LIBS            = -lm -lpthread
  RELEASE_LDFLAGS = -Wl,--gc-sections -Wl,--as-needed
else
  LIBS            = -lm
  RELEASE_LDFLAGS = -Wl,-dead_strip
endif
```

HarmonyOS PC 上 `uname -s` 返回 `HarmonyOS`（不是 `Linux`），分支落入 else，
拿到 **macOS 专属** `-Wl,-dead_strip`，链接报错：

```
ld.lld: error: unknown argument '-dead_strip'
clang-15: error: linker command failed with exit code 1
```

## 根因与机制

1. 上游把平台假设建模为"Linux / 其他"，`其他` 分支里堆了 macOS 专属参数；
2. HarmonyOS 的 `uname -s = HarmonyOS` 既不是 `Linux` 也不打算进 macOS 分支，
   却因 ifeq 二分支结构被挤进 macOS 分支；
3. `-Wl,-dead_strip` 是 ld64（macOS）参数，ld.lld（Linux/HarmonyOS 工具链）不识别。

## 修复（分支反转，Darwin 专属化）

把"默认/通用"与"专属"的位置互换，只有真正的 macOS 走专属分支：

```make
ifeq ($(UNAME_S),Darwin)
  LIBS            = -lm
  RELEASE_LDFLAGS = -Wl,-dead_strip
else
  LIBS            = -lm -lpthread
  RELEASE_LDFLAGS = -Wl,--gc-sections -Wl,--as-needed
endif
```

等价于"黑名单"改"白名单"：识别不出或新平台一律走通用参数，不会吃到别的平台的专属 flag。

## 验证

- `make release` / `make lib`（补丁后）→ exit 0，产物 librayforce.a + rayforce CLI 正常；
- `conan create`（ohos-aarch64 profile，conan-verify G2）→ PASS；
- 专项测试 `test_ohos.c` 与消费者 `test.c` 运行 exit 0。

## 适用边界

- 适用：任何以 `uname -s` 做 `ifeq` 平台分支、且"非 Linux 即 macOS"假设的 raw Makefile；
- 反例/不适用：
  - 带 `ifeq ($(origin X), undefined)` 守卫的探测段 → 应走注入方案（见
    DRAFT-makefile-origin-guard-dep-injection）；
  - autotools → 走 E007/E160 config.guess 方案；
  - CMake → CMAKE_SYSTEM_NAME=HarmonyOS 有原生支持，无需此补丁。

## 查重差异（与既有知识的关系）

- similar_to: DRAFT-makefile-origin-guard-dep-injection（同为 raw Makefile × HarmonyOS 平台探测，
  方案不同：注入跳过探测 vs 源码分支反转）；
- similar_to: E392（raw Makefile × Conan 配方层陷阱，层不同：配方层 vs Makefile 内部）；
- 七轴：combination_novelty=true，boundary_novelty=true，无 exact/causal 重复。
