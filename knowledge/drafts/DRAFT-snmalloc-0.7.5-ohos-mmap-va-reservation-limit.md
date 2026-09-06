# DRAFT-snmalloc-0.7.5-ohos-mmap-va-reservation-limit：OHOS mmap 虚拟地址空间预留上限

## 现象

snmalloc 0.7.5 在 HarmonyOS PC（aarch64）上执行上游测试时，所有 check 变体
（`SNMALLOC_CHECK_CLIENT`）启动即失败：

```text
Failed to initialise snmalloc.
Signal 6 (core dumped)
```

`perf-startup-check`、`func-malloc-check` 等 31 个测试在初始化阶段 SIGABRT，
fast 变体大多通过。错误点在 `src/snmalloc/ds/pagemap.h`：`PAL::reserve`
返回 `nullptr` 后调用 `PAL::error("Failed to initialise snmalloc.")`。

## 根因

平台实测：HarmonyOS 对单次 mmap 匿名映射的虚拟地址空间预留有上限——
256GB 成功、384GB 失败（errno=12 ENOMEM）。而 snmalloc check 变体默认启用
`full_checks` mitigations（含 `random_pagemap`），`FlatPagemap::init()`
按 `REQUIRED_SIZE + 4*next_pow2(REQUIRED_SIZE)` 预留：

- `MIN_CHUNK_BITS=14`、`address_bits=48`、`sizeof(PagemapEntry)=16`
  → `REQUIRED_SIZE = 2^(48-14) × 16B = 256GB`
- 加 randomize 放大 → 约 1280GB，远超平台上限 → `mmap` ENOMEM → 初始化失败

fast 变体（`no_checks`，无 `random_pagemap`）仅预留 256GB，恰好低于上限，
因此大多通过。

## 可复用修复模式

HarmonyOS 上需要超大虚拟地址空间预留给 pagemap/metadata 的分配器类库，
应检测平台 mmap 单次预留上限并：

1. 优先在 mitigation 层禁用仅影响预留量的随机化项（`random_pagemap`），
   保留其余全部检查——参照上游已有平台特例先例（OPEN_ENCLAVE 禁用
   `metadata_protection + random_pagemap`、NetBSD 禁用 `pal_enforce_access`）；
2. 修改点：`mitigations.h` 增加 `#elif defined(__OHOS__)` 分支，
   `CHECK_CLIENT ? full_checks - random_pagemap : no_checks`；
3. 验证：重新 `cmake --build` 后 `ctest`，check 变体从 31 失败降至 10 失败，
   总体通过率 61% → 88%（70/80）。

备选（不推荐首选）：增大 `MIN_CHUNK_BITS` 缩小 pagemap（上游
`SNMALLOC_QEMU_WORKAROUND` 思路），但会改变分配粒度语义，且该宏需
`SNMALLOC_VA_BITS_64` 同时定义才生效，实测未改变预留量。

## 验证证据

- 平台 mmap 预留上限探针：256GB OK / 384GB FAIL（ENOMEM）
- 适配前：ctest 61% 通过（49/80），check 变体 31 失败
- 适配后：ctest 88% 通过（70/80），check 变体 10 失败（剩余为 libc 覆盖 +
  多线程交互类平台差异：miracle_ptr / multi_atexit / multi_setspecific /
  multi_threadatexit / new，与 mmap 预留无关）
- Conan：`conan-verify` G0-G4 全过（ohos-aarch64 profile）

## 适用边界与反例

- 适用：HarmonyOS 平台、需大虚拟地址空间预留给 pagemap 的分配器库；
  check/检测变体启用 random_pagemap 类 mitigation 时。
- 反例：普通 Linux（overcommit 允许大预留）无需禁用；非分配器库（预留量
  小）不受影响；`SNMALLOC_CHECK_CLIENT_MITIGATIONS` 已显式自定义的构建
  不受默认 mitigations 分支影响。
- 限制：禁用 random_pagemap 会降低对 pagemap 位置被恶意预测的防御，
  属平台能力约束下的权衡；不得把 check 变体测试整体跳过或标记通过来掩盖。
