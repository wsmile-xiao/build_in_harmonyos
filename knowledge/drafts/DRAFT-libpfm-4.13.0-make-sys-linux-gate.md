# Makefile 库在 HarmonyOS 上 uname -s 返回 "HarmonyOS" 导致 `ifeq ($(SYS),Linux)` 门控源文件未编译 → undefined symbol

## 问题描述

libpfm 4.13.0（libpfm4，性能监控库）适配 HarmonyOS PC (aarch64) 时，`make` 顶层构建成功、libpfm.a 生成，但下游链接 `tests/validate` 报：

```
ld.lld: error: undefined symbol: pfm_arm_perf_validate_pattrs
>>> referenced by pfmlib_arm_armv8.c ... in archive .../lib/libpfm.a
>>> referenced 141 more times
```

大量 ARM64 perf_event 符号缺失。

## 根因

libpfm4 的构建是纯 Makefile（`Makefile` + `config.mk` + `rules.mk`），`config.mk` 用：

```make
SYS := $(shell uname -s)
```

探测操作系统，而 `lib/Makefile` 把 Linux 专属源文件（perf_event 支持，如 `pfmlib_arm_perf_event.c`、`pfmlib_perf_event_pmu.c` 等）挂在：

```make
ifeq ($(SYS),Linux)
SRCS += pfmlib_arm_perf_event.c
endif
```

HarmonyOS 上 `uname -s` 返回 **`HarmonyOS`**（而非 `Linux`），因此这整段源文件没有被编译进 `libpfm.a`，下游引用其符号时报 undefined symbol。这与"平台不识别"类问题（E007 config.guess、E090 meson host_system）同族，但发生在 **make + uname -s 门控** 路径上，E090 仅覆盖 meson。

## 解决方案

构建时用 make 变量覆盖 `SYS=Linux`（HarmonyOS 内核即 Linux 系，`perf_event_open` 等接口存在），使 Linux 门控源文件进入编译。**零源码改动**：

```bash
make -j1 SYS=Linux CC=/data/service/hnp/bin/clang ARCH=aarch64 \
     CONFIG_PFMLIB_NOPYTHON=y \
     'DBG=-g -Wall -Werror -Wextra -Wno-unused-parameter -Wno-error=unused-but-set-variable -Wno-error=#warnings'
```

验证库内 perf_event 对象已进入：

```bash
ar t lib/libpfm.a | grep -c perf_event   # -> 6
```

## 验证

- 覆盖前：`tests/validate` 链接失败（undefined symbol pfm_arm_perf_validate_pattrs 等 141+ 引用）。
- 覆盖后：libpfm.a 含 6 个 perf_event 对象；`tests/validate` 链接通过并运行：74 个 PMU 事件表检查全部 Passed、51 个 ARM64 断言 0 errors、3 个 perf 断言 0 errors。
- `conan create` + test_package（含 HarmonyOS 专项测试）2/2 通过。

## 适用范围与反例

- **适用**：所有以 `uname -s` 探测 `SYS` 且用 `ifeq ($(SYS),Linux)` 门控源文件的 Makefile 型 C/C++ 库（HarmonyOS/OHOS 目标）。
- **反例**：若库对 `SYS` 分支有更强耦合（SYS 决定头文件路径、条件编译符号），仅覆盖 SYS 可能不够，需配合 sed 替换或补丁；autotools 库走 E007（config.guess）路径，meson 库走 E090 路径。

## 关联候选（R02 复核后更新）

- **K3（R02 修正：ABI 自检 mismatch 根因实证为可修 musl 宏缺口）**：libpfm 上游 `validate.c` 的 5 个 struct ABI 自检（`PFM_PMU_INFO_ABI0` 等）在 64 位 aarch64 报 mismatch（44 vs 56 / 48 vs 64 / 48 vs 64 / 20 vs 32 / 28 vs 40）。R02 探针实证根因：**OHOS musl 未定义 `__WORDSIZE`**（`_LP64` 已定义而 `__WORDSIZE=UNDEFINED`），`pfmlib.h` 的 `#if __WORDSIZE == 64` 落入 else 分支取 32 位 ABI0 常量，与实际 64 位布局不符。属**可修** musl libc 宏缺口（libc 探针类）：配方 make DBG 注入 `-D__WORDSIZE=64`（等价 glibc aarch64 行为）后 validate 输出 `All tests passed`（rc=0，5 mismatch→0，74 表 + 51 ARM64 + 3 perf 仍全过）。恢复条件：工具链定义 `__WORDSIZE` 或上游改用 `_LP64`/`__LP64__`。R01 曾暂记为"上游校准伪影"，**R02 实证为可修缺口，以本条目为准**。
- **K5（R02 新增：x86 事件表在 aarch64 交叉目标硬阻塞）**：开启 `CONFIG_PFMLIB_ARCH_X86=y` 后 `lib/pfmlib_amd64.c:325 asm volatile("cpuid")` 编译失败——cpuid 为 x86 独有 ISA，aarch64 无此指令/寄存器。阻塞归属=真实平台/ISA 硬阻塞，非配方可修；恢复条件=仅 x86_64 目标或带 cpuid 指令模拟的工具链。与 E016（asm 不支持→disable-asm）同族但方案不同：本场景 cpuid 是 PMU 识别核心逻辑，无 no-asm 等价开关。
- **K1（R02 强化）**：SYS 门控修复（`SYS=Linux` 覆盖）之外，R02 逐类最小纳入实证 `CONFIG_PFMLIB_ARCH_MIPS/y`（14 通过）、`ARM/y`（32 通过）、`POWERPC/y`（31 通过）均可在 OHOS aarch64 实际构建运行 0 errors——架构门控值可独立开启，仅 x86 因 cpuid 硬阻塞不可。
- **K4（保持 R01）**：libpfm 默认只编码本机检测到的 PMU 事件；交叉/容器宿主 PMU 集不同时，消费者测试须在 `pfm_initialize()` 前 `setenv("LIBPFM_ENCODE_INACTIVE","1",1)`，否则 `pfm_get_event_encoding("arm_ac57::CPU_CYCLES")` 报 "event not found"（harmonyos_test.c 已如此实现并 2/2 通过）。
- **K2（保持 R01）**：clang15 + 上游默认 `-Werror` 的两类误报（`unused-but-set-variable`、OHOS sysroot `<sys/poll.h>` 重定向 #warning），用 make `DBG=...-Wno-error=unused-but-set-variable -Wno-error=#warnings` 最小放宽；其中 sys/poll.h 部分与既有 E203 重叠，仅记增量。

## 查重摘要（七轴）

| 候选 | exact | causal | trigger | solution | combination | boundary | test_migration |
|------|-------|--------|---------|----------|-------------|----------|----------------|
| K1 (SYS 门控) | no | no | partial(E090) | low(E090) | yes | yes | no |
| K2 (-Werror) | no | partial(E203) | high(E203)/partial(E063) | high(E203)/partial(E063) | yes | yes | no |
| K3 (ABI 自检) | no | no | low | low | yes | yes | no |
| K4 (ENCODE_INACTIVE) | no | no | no | no | yes | yes | no |

**路径判断**：任务类型=知识库扩展；K1/K3/K4 查重未命中或部分覆盖且经本轮真实日志验证、可跨库复用 → **路径 B（new_draft）**；K2 与 E203/E063 部分重叠，仅记增量差异，复用既有条目。