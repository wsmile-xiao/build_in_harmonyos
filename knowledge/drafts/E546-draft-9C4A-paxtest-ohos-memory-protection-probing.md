# E546 草稿：OHOS 内核内存保护/ASLR 的探针测量与解读口径（含非 x86 探针适配）

> 来源：paxtest 0.9.15 适配（task #9339，分支 `feat/paxtest-0.9.15`，2026-09-27，
> HarmonyOS PC / HongMeng Kernel 1.12.0 / aarch64 / clang 15.0.4）。
> 关联：E045（W^X 事实：libffi/ctypes RWX→EINVAL）、
> DRAFT-boxfort-ohos-code-page-integrity（代码页完整性 XPM 四条自改代码路径被封死）、
> DRAFT-gas-arm64-clang-integrated-as（匿名 `mmap(PROT_EXEC)` 实测可用）——
> 本条补的是**"如何测量与解读"**这一层，不重复它们的"保护事实"与"软件绕行"。

## 一、适用场景（一类问题）

任何需要**判定 OHOS 内存保护 / ASLR 能力**或**移植安全探针类套件**的场合：

- 安全评估、加固假设验证、取证取证结论；
- JIT / trampoline / 沙箱 / 自修改代码等"依赖可执行内存"能力的可行性预判（与 E045、boxfort 草稿互补）；
- 把 Linux/PaX 生态的安全回归、基准、探测类套件（paxtest、checksec 类、mitigation 探针）搬到 OHOS/aarch64。

## 二、问题本质：测量本身会骗人（三类失效）

1. **判定力盲区**：探针的"正判定"依赖目标架构的最小 shellcode；上游 `shellcode.h` 无 aarch64
   分支时回退到 x86 的 `RET`(0xC3)，在 ARM64 上**可执行页与不可执行页都表现为进程被信号终止
   （Killed）**——15 项 exec 探测全部退化为盲判（修复前实测）。
2. **语义误读**：`Killed` 只表示"攻击尝试未成功"，**不等于"保护存在"**（盲判时同样 Killed）；
   `N quality bits` 是 1500 次采样的熵估计，不是安全保证。
3. **平台差异**：OHOS 的 W^X/XPM、procfs（无 `[vdso]`）、aarch64 返回地址语义（x30）、clang
   实现差异，使部分测试项**不可测或语义失效**，必须显式列明而非默默算通过。

## 三、根因分解

| # | 现象（探针视角） | 根因 |
|---|---|---|
| 1 | exec 系 15 项在修复前一律 Killed | `shellcode.h` 无目标架构分支 → x86 `RET` 在 ARM64 无法构成"执行后正常返回"序列 |
| 2 | `mprotect` 变体同样 Killed | OHOS 内核 W^X：`mprotect(RWX)` 类请求被拒/触发代码页完整性（XPM）击杀（与 E045/boxfort 实测一致） |
| 3 | `writetext` Killed | 代码页不可改写（XPM；`/proc/self/mem`、`MAP_FIXED` 覆盖亦被拒，见 boxfort 草稿） |
| 4 | `VDSO randomization` 中止：`./getvdso: No error information` | OHOS `/proc/self/maps` 无 `[vdso]` 条目 → getvdso 无输出 → randbody fscanf 失败 |
| 5 | `Return to function (memcpy)` 无输出 | aarch64 返回地址在 x30 寄存器而非栈帧，256B 栈溢出未劫持控制流，子进程正常退出 |
| 6 | `blackhat` 打印 INFO 后按 kiddie 语义运行 | 上游 `body.c` blackhat 技巧依赖 GCC 嵌套函数；clang 构建走 `#ifdef __clang__` 回落 |
| 7 | `chpax` 报 `Wrong architecture`，`paxbin` 为 no-op | 上游 ELF 机器列表无 EM_AARCH64；OHOS 无 PaX 标志可设（惰性工具，不影响测试语义） |

> 注意 1 与 2 的**方向相反**：修复 1 是让"可执行页"能被识别为 Vulnerable（正判定）；2 是内核
> 真实拒绝把数据页变可执行。若不做 1 就直接引用 2 的 Killed 结论，会把"探针盲判"误当成"保护实证"。

## 四、可复用方法（推荐路径 `fix-probe-arch-then-run-matrix`）

1. **先恢复判定力**（最小、可移植的源码补丁）：
   - aarch64：`SHELLCODE_RETURN "\xc0\x03\x5f\xd6"`（ARM64 `ret`，小端）；ARM32/PPC/SPARC
     上游已有分支可参照；
   - 原则：补丁是**架构分支**（`#elif defined(__aarch64__)`），不注入平台宏、不改判定逻辑。
2. **按"内存类别 × 操作"矩阵实测**（逐项保留原始输出）：
   - exec 系（anon/bss/data/heap/stack/shlib·bss/data）× {直接执行, mprotect 后执行}；
   - writetext（改写 text 段）；
   - 随机化：13 项 randbody（每项 1500 次采样）+ 2 项 fastrandbody（内存耗尽场景）；
   - rettofunc 4 项。
3. **解读口径**（本项目采用的表述模板）：
   - `Killed` = 攻击尝试被信号终止（目标内存不可执行/不可写——**属保护生效的表现，但须先确认
     探针具备正判定力**）；
   - `Vulnerable` = 攻击代码实际执行成功（保护缺失，需关注）；
   - `N quality bits` = 随机化熵估计（相对比较用），**不是安全保证**；
   - 不可测项单列并写明原因（不要计入"通过率"）。
4. **列明判定盲区**（交付物必须包含）：无 arch shellcode 时的盲判、VDSO 不可测、rettofunc 的
   体系结构差异、blackhat 在 clang 下的降级、工具链侧（chpax 惰性）等。
5. **与邻近知识互证**：把探测结果与 E045（W^X）、boxfort（XPM）对照——二者从"软件症状"侧给出
   保护事实，本条目从"探针测量"侧给出可复现矩阵，互相印证而非重复。

## 五、实测结果矩阵（paxtest 0.9.15，真机）

**攻击探测（kiddie 与 blackhat 两轮一致）：15/15 `Killed`，无一 `Vulnerable`**

```
Executable anonymous mapping / bss / data / heap / stack              : Killed          （5）
Executable shared library bss / data                                  : Killed          （2）
Executable *（mprotect 变体：anon/bss/data/heap/stack + 共享库 bss/data）: Killed       （7）
Writable text segments                                                : Killed          （1）
```

**随机化测量（kiddie 一轮；blackhat 一轮为采样涨落，如 main ET_EXEC 21↔22）**

```
Anonymous mapping: 19 | Heap(ET_EXEC): 19 | Heap(PIE): 19
Main executable(ET_EXEC): 21 | Main(PIE): 22 | Shared library: 21
VDSO: 中止（/proc/self/maps 无 [vdso]）
Stack(SEGMEXEC/PAGEEXEC): 21 / 21 | Arg/env(SEGMEXEC/PAGEEXEC): 21 / 21
Offset to library(ET_EXEC/ET_DYN): 23 / 23 | 内存耗尽(@~0/@0): 22 / 22
```

**返回攻击**：`rettofunc strcpy`/`strcpy PIE` = `return address contains a NULL byte.`
（上游守卫分支）；`memcpy`/`memcpy PIE` = 无输出（aarch64 x30 语义，见根因表 #5）。

**解读**：数据页"直接执行"与"mprotect 后执行"在 OHOS 上均不可行；ASLR 覆盖 12 类、熵约
19–23 bits。与 gas 草稿的对照值得写清：**匿名 `mmap(PROT_READ|PROT_EXEC)` 允许**（gas 实测），
但**把已存在的可写页变为可执行（RWX / mprotect 加 EXEC）被拒**——paxtest 探测的正是后者。

## 六、与现有知识库的边界（查重结论，2026-09-27 实查）

| 条目 | 讲什么 | 与本条的边界 |
|---|---|---|
| E045 | W^X 事实：libffi/ctypes 的 RWX 分配→EINVAL（用户态症状） | 本条是"系统性探针测量 + 解读口径"，给出逐内存类矩阵与判定盲区清单 |
| DRAFT-boxfort-ohos-code-page-integrity | 代码页完整性（XPM）四条自改代码路径被封死 + 子进程探测技巧 | 本条不重复路径枚举；补"攻击面矩阵 + ASLR 质量 + 结果语义" |
| DRAFT-gas-arm64-clang-integrated-as | dynarec 视角：匿名 `mmap(PROT_EXEC)` 可用、GAS 汇编可用 | 本条给出两者的区分口径（"新建可执行映射"vs"改造既有页"） |
| DRAFT-libffcall-2.5-trampoline-exec-page | 构建期 trampoline 适配模式 | 属软件绕行；本条属测量/解读 |
| E246（seccomp/SIGSYS） | 系统调用拦截面 | 不同机制：seccomp 拦 syscall vs 内核内存页属性/完整性 |
| index 关键词实查 | `paxtest`/`shellcode`/`exec stack` 全 0 命中；`ASLR` 仅 E222（FaultLogger） | 无同类"探针测量与解读"条目 |

## 七、验证与复现

```sh
# 1) 构建与消费者测试（OHOS 目标）
conan create archives/p/paxtest/0.9.15 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device \
  --build=missing --user=ohpcd --channel=stable     # test_package 21/21 断言
# 2) 真机全量两轮（逐项原始输出见 archives/p/paxtest/0.9.15/reports/device-*.log）
cd <pkg>/bin/paxtest
./paxtest kiddie  "$LOG.kiddie"     # rc=0；15/15 Killed；12 项 bits；VDSO 中止
./paxtest blackhat "$LOG.blackhat"  # rc=0；攻击面与 kiddie 一致 + INFO 回落说明
# 3) 判定力对照（回归用）：若在允许可执行内存的环境跑同套件，exec 正例应返回 Vulnerable
```

配套补丁（paxtest 0.9.15）：`patches/0005-shellcode.h.patch`（aarch64 分支）；
另有 `patches/0001..0004`（chpax 移除 a.out 支持，属构建期 portability，独立于本条方法论）。

## 八、适用边界

- 本条目面向**测量与解读**；具体"如何绕行/适配"某一软件（JIT、trampoline、沙箱）请见 E045、
  boxfort、libffcall 等条目。
- 探针矩阵数字与内核版本相关（本机 HongMeng Kernel 1.12.0）；跨版本/跨设备比较需重测。
- `Killed` 的强解读需要"探针具备正判定力"这一前提（本条目第 1 步）；缺少该前提时应按盲判处理。
