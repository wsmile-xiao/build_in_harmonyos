# DRAFT-ohos-software-register-model-for-absent-hw-facility：缺失硬件控制寄存器用软件寄存器镜像建模

- **来源**：paflib 0.3.0 OHOS aarch64 适配（2026-10-03，contrib-9274，分支 `feat/paflib-0.3.0`）
- **类别**：跨架构移植 / API 兼容（portability / api / compat / runtime）
- **相邻条目**：E213（本地实现缺失 API——补单个接口；本条是"把一个**有状态寄存器**的 set/get 状态机整体建模"）；与 `DRAFT-ohos-perf-event-open-denied-substitute-event-source` 同为"能做实就做实"的缺口处置。

## 现象

一类库的公开 API 只是读写**某个硬件控制寄存器**，例如 Power 架构：

- **DSCR**（Data Stream Control Register）：`paf_dsc_get/set`，SPR 0x03/0x11；
- **PPR**（Program Priority Register）：`or Rx,Rx,Rx` 编码优先级。

在 OHOS/aarch64 上：

1. **编译期**：`paf-common.h` 的 `mfspr`/`mtspr`/`sync` 是 PowerPC inline asm，直接编译失败；
   `dsc.c` 的能力探测还用了 `SIGILL` + `ucontext.uc_mcontext.regs->nip`（Power 专有字段）。
2. **运行时**：aarch64 没有这些寄存器。

## 常见但不理想的处置

"整个 API 一律返回 `ENOSYS`"。这对"读不到就报不可用"是合理的，但对 **有状态** 的
set/get 过于粗暴：调用方会认为平台完全不能用，连"set 后能取回原值"的状态往返都做不了。

## 推荐处置：线程局部软件寄存器镜像 + 完整特性掩码

只要 API 语义是"对一个**有状态**寄存器做读写与合法性校验"，就把它建模成软件寄存器：

1. 用 `__thread` 保存寄存器镜像（保证"每线程一份"，与硬件语义一致）；
2. `check_support()` 返回**完整特性掩码**（如 `DSCR_ISA_2_07_MASK`），让上层走正常的
   set/get 分支，而不是走"不支持"分支；
3. `get` 返回镜像；`set` 先按掩码校验（`(value|mask) != mask` → `EINVAL`），再存入镜像；
   返回码/errno 与硬件版保持一致；
4. 架构专属探测（`SIGILL`/`ucontext`/`mfspr`）用 `#if defined(__powerpc__)` 守卫，原逻辑保留。

**边界**：只有"有状态寄存器"值得建模；**无状态、纯硬件副作用**的设施（如 PPR 的优先级
提示、`paf_yield`）应降级为 no-op——它们没有可保存的状态。

## 验证证据（paflib DSCR）

```
# 上游 test_dsc（软件模型下走完整路径）：exit 0
# 消费者断言（域内）：
PASS: paf_dsc_check_support reports a non-empty mask
PASS: DSCR mask is the full ISA 2.07 mask
PASS: paf_dsc_set accepts DPFD field
PASS: paf_dsc_get reflects DPFD field
PASS: paf_dsc_set(0) then get == 0
PASS: paf_dsc_set rejects out-of-mask bits with EINVAL
（消费者 19/19；上游 13 项中 12 项真实执行并通过）
```

## 禁止做法

- 对所有设施一律 `ENOSYS`，不区分"有状态寄存器"与"无状态提示"；
- `set` 只 `return 0` 却不真正保存镜像（破坏 set/get 往返，测试必失败）；
- 报告"支持"却宣称有硬件效果（软件模型只保证 API 语义，不产生硬件副作用）；
- 直接删除公开 API（破坏 ABI）。
