# E543-draft-A7F3 — aarch64 协程上下文切换汇编模式

## 错误面
- **触发**：make/clang/运行时（协程库从 x86 移植到 aarch64）
- **阶段**：compilation/runtime
- **签名**：`Segmentation fault` / `invalid output constraint` / 协程首次切换即崩

## 识别
- severity: 3（🔴blocking）
- category: platform, portability, aarch64, coroutine, assembly, ohos

## 诊断
ARM64 的 `BL` 指令**不压栈返回地址**（返回地址在 x30/LR），照搬 x86_64
协程库的 call/ret 栈式语义会导致恢复上下文时跳错地址或 sp 错乱——
libco v1.0 的 coctx_swap.S 仅有 i386/x86_64 实现，直接移植即触发。

## 方案
按 x86_64 原版"存/取 regs 数组"语义重写 aarch64 段：

1. `coctx.h`：`coctx_t.regs` 扩为 24 槽
2. `coctx.cpp`：`coctx_make` 槽位常量 kA64SP=12 / kA64RETAddr=13 /
   kA64X0=22 / kA64X1=23（ss_sp 按 16 字节对齐）
3. `coctx_swap.S`：保存 x19-x28（callee-saved）、x29/x30（fp/lr）、
   real sp→槽 12、resume 地址→槽 13、d8-d15（callee-saved FP）、
   参数 x0/x1→槽 22/23；恢复后 `mov sp, x9; br x8`

验证：libco 8 个 example 全过（含 10 万次切换 copystack 压测）。
参考补丁：`archives/l/libco/1.0/patches/0004-coctx_swap.S.patch`

## 禁止
- ❌ `stp x*, x30, [sp, #-16]!` 存返回地址——aarch64 BL 不写栈，
  参数/返回地址走寄存器，槽位错乱=首切即崩
