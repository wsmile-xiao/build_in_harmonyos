# DRAFT: aarch64 mcontext 单步适配（Darwin/x86 专属 __ss.__rflags -> pstate SS 位）

- 来源库：access_profiler 20260924（arvidn/access_profiler）
- 类型：路径 B 知识草稿（信号处理器/ucontext 移植，跨库可复用）

## 问题

上游 `access_profiler.cpp` 的两个信号处理器（segv_handler / single_step_handler）
用 ucontext 启停 CPU 单步（保护页 + SIGSEGV/SIGTRAP 记录堆对象字段访问热区）：

```cpp
#ifdef __LP64__
    uc->uc_mcontext->__ss.__rflags |= 0x100;   // 开单步
#else
    uc->uc_mcontext->__ss.__eflags |= 0x100;
#endif
```

`__ss`/`__rflags`/`__eflags` 是 Darwin/x86（及 x86 glibc）的 ucontext 布局。
OHOS aarch64 的 `mcontext_t`（sigcontext）没有 `__ss` 成员，且 `uc_mcontext`
本身不是指针，直接编译失败：

```
error: member reference type 'mcontext_t' (aka 'sigcontext') is not a pointer
error: no member named '__ss' in 'sigcontext'
```

共 4 处编译错误（两个 handler 各 2 处）。

## 根因

上游仅实测 macOS/x86（README 自述 "only tested on mac"）；`__LP64__` 分支依赖
Darwin/x86 的 ucontext 间接成员布局，不是 POSIX/aarch64 可移植写法。

## 修复

用标准架构宏 `__aarch64__` 分支改为直接成员访问 aarch64 PSTATE 的 SS
（Software Step）位（bit 21 = 0x200000）：

```cpp
#ifdef __aarch64__
    uc->uc_mcontext.pstate |= 0x200000;      // 开单步
#elif defined(__LP64__)
    uc->uc_mcontext->__ss.__rflags |= 0x100;
#else
    uc->uc_mcontext->__ss.__eflags |= 0x100;
#endif
```

single_step_handler 中对称改为 `pstate &= ~0x200000` 关单步。补丁使用标准架构宏，
不含 `__OHOS__` 平台宏（符合 R8/PF5）。

## 验证

| 项目 | 结果 |
|------|------|
| 修复前编译 | 4 处 error（no member '__ss'） |
| 修复后编译 | exit 0 |
| 上游测试 test | exit 0，stdout=55，access_profile.out = `test / 52: 1`（与上游 README release 输出一致 → SIGSEGV/SIGTRAP 单步路径实际生效） |
| conan create（G2 干净构建） | exit 0 |
| W3 本地 CI | L0/L1/L4/L5 pass |

## 适用边界

- 适用：aarch64 Linux/OHOS 上使用 ucontext 单步（mprotect + SIGSEGV/SIGTRAP）
  或信号处理器内修改 CPU 标志寄存器的 C/C++ 库；任何上游写 Darwin/x86 专属
  `uc_mcontext->__ss` 的代码都可用本模板改写。
- 反例/不适用：x86/x86_64 原生构建（`__LP64__` 分支仍可用，勿改）；需要兼容
  macOS 的跨平台库应保留原分支（本补丁正是如此设计）；非信号处理器场景的
  mcontext 访问按目标架构单独核对布局。

## 查重与关系

- 四范围查重（正式知识/图谱索引/草稿/正式文档）均未命中：E051/E246（内核信号
  送达/SIGSYS）、E222/E462（ptrace 被禁时的诊断方法）、E224（signalStack 释放
  类崩溃）均不涉及 mcontext 单步移植。
- 七轴：exact=false, causal=false, trigger=partial(信号处理+OHOS 面),
  solution=false, combination=true, boundary=true, test_migration=true。
- similar_to/caused_by/prerequisite_of/conflicts_with: 无。

## 关联交付

- 本草稿与 `archives/a/access_profiler/20260924/**` 在同一 PR 交付；
  草稿仅保留在 `knowledge/` 根目录，不修改正式知识图谱/文档/索引。