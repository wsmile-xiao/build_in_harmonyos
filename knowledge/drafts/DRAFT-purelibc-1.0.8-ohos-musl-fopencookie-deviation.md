# OHOS musl fopencookie 偏离：同步 FILE 虚拟化在鸿蒙 PC 上不可用

**状态**：DRAFT（关联 purelibc/1.0.8 适配 PR）｜**严重度**：3（平台级能力缺失）｜**类别**：ohos/libc/runtime

## 症状（稳定复现）

任何基于 `fopencookie()` 的 FILE I/O 虚拟化设计在 OHOS（HarmonyOS PC，musl libc）上表现异常：

- `fwrite()` 正常返回，但数据**不会同步**到达注册的 `cookie_write` 回调；
- `fclose()` 返回 **-9（EBADF）**，即使写入路径完全合法；
- `cookie_close` 回调**从不触发**；
- `cookie_write` 的两次触发均发生在**进程退出阶段**（fclose 返回值已定格之后）。

## 最小复现（不涉及任何三方库，排除包内问题）

```c
#define _GNU_SOURCE
#include <stdio.h>
static ssize_t cw(void *ck, const char *b, size_t n) {
    /* ck 与注册指针一致（0x1234 MATCH），排除调用方传参错误 */
    return n;
}
static int cc(void *ck) { return 0; }   /* 从未被调用 */
int main(void) {
    cookie_io_functions_t funcs = {NULL, cw, NULL, cc};
    FILE *f = fopencookie((void *)0x1234, "w", funcs);
    fwrite("hello", 1, 5, f);
    int r = fclose(f);          /* 返回 -9 */
    return 0;
}
```

探针完整源码与运行记录见 purelibc 适配分支 notes.md（GLM-61，2026-09-20）。

## 排除过程

1. 先怀疑 purelibc 配方/补丁：消费者测试经 stdio 路径退出码 4（fclose≠0）。
2. 改用直接 writev 处理 → 依旧：排除 stdio 缓冲路径差异。
3. 30 行独立探针（上）在设备上复现 → **平台问题实锤**。
4. diff 上游 purelibc 1.0.8 ↔ 1.0.10 的 stdio.c：仅空白与 glibc 2.39 fileno 兼容差异
   → 上游未修此路径，非上游回归。

## 根因

OHOS 使用的 musl 变体在 `fopencookie` 实现上偏离 glibc 与原版 musl：cookie 回调的
触发时机被推迟到进程退出刷新阶段，close 回调链路缺失，fclose 以 EBADF 失败。
所有依赖"cookie 回调同步到达"的 FILE 虚拟化设计（purelibc stdio 层、BSD funopen
移植、日志/重定向 fd 包装器）在该平台无法工作。

## 处置方案（已在 purelibc 1.0.8 适配中验证）

1. **先探针后动手**：平台问题必须用独立探针实锤，避免把平台缺陷误诊为配方 bug 无限调参。
2. **门控回退**：`#if defined(__GLIBC__)` 包住 cookie 覆盖层；musl 下经
   `dlsym(RTLD_NEXT, ...)` 惰性指针回退 libc 同名实现——glibc 上逐位保持上游行为。
3. **测试面收缩**：消费者测试改测可移植层（直接 syscall 包装器截获：open/write/close →
   `_pure_syscall` → 用户处理器），glibc/musl 断言一致。
4. **透明降级**：notes.md / PR 正文写明哪些层在 OHOS 不可用及证据，不静默交付会丢数据的层。

## 适用范围与反例

- 适用：任何在 OHOS 上使用/移植 fopencookie 的包（虚拟化、审计、透明重定向类库）。
- 不适用：glibc 环境（行为正常）；不依赖 cookie 同步性的场景（如仅用 fopencookie 做
  一次性格式转换、进程退出时统一冲刷也可接受的设计）。
- 解除条件：OHOS musl 修复 fopencookie 同步语义后，门控回退可整体摘除。
