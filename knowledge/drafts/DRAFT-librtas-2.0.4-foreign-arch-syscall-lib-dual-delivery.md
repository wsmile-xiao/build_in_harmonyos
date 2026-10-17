# DRAFT-librtas-2.0.4-foreign-arch-syscall-lib-dual-delivery

> 外架构 syscall 封装库：主库不可运行 + 副库架构中立时的双库交付与测试处置
> 来源：librtas 2.0.4 适配 HarmonyOS PC（OHOS aarch64）
> 状态：草稿，待主编审核

## 问题

碰到「一个包同时交付主库与副库，主库整体封装**另一 CPU 架构**的内核 syscall /
firmware ABI，副库是纯数据解析器」的组合时，怎么判定能不能适配、怎么交付、
测试怎么写，才既不裁剪软件也不伪造可用。

本条补齐知识库里 E237、E245 之外的**第三种形态**：

| 条目 | 形态 | 处置 |
|------|------|------|
| E237（acpid） | 守护进程主体逻辑有用，只是事件源接口缺失 | 编译验证 + 如实声明 |
| E245（vhangup） | 目标架构**内核 syscall 存在**，仅 libc 未封装 | 可写 syscall shim |
| **本条（librtas）** | 目标架构**内核根本没有该 syscall**，失效面覆盖主库全部入口 | 双库原样交付 + 分层断言 |

## 一手案例：librtas 2.0.4

主库 `librtas.so` 的每个公开入口最终都走：

```c
/* librtas_src/syscall.h */
#define __NR_rtas 255
/* librtas_src/syscall_calls.c */
rc = syscall(__NR_rtas, &args);        /* + "ibm,*" PowerPC RTAS token */
/* librtas_src/ofdt.c */
static const char *ofdt_rtas_path = "/proc/device-tree/rtas";
```

证据链（6 条，全部实测或可核对）：

1. **上游自述**：README 首段 —— "user-space access to the Run-Time Abstraction
   Services (RTAS) **on the ppc64 architecture**"。
2. **syscall 硬编码**：`__NR_rtas 255`，`struct rtas_args` 注释
   "Based on include/asm-ppc64/rtas.h"。
3. **aarch64 无此 syscall**：`clang -target aarch64-linux-ohos -E -dM` 中
   `__NR_rtas` 出现 **0** 次。
4. **设备树路径**：`/proc/device-tree/rtas` 是 PowerPC OFDT 节点，aarch64 不存在。
5. **发行版佐证**：Debian/Ubuntu 打包 `Architecture: powerpc ppc64 ppc64el`，
   **不构建** amd64 / arm64。
6. **运行期实测**（aarch64 产物经 binfmt/qemu 实际运行）：
   `rtas_get_time()` / `rtas_delay_timeout()` 返回 librtas 自有负码
   （root 下 `RTAS_KERNEL_INT=-1001`，非 root `RTAS_PERM=-1003`）。

## 为什么不能 shim（与 E245 的判据差异）

E245 的 vhangup 之所以能 shim，前提是**目标架构内核里那个 syscall 存在**
（aarch64 `SYS_vhangup=58`），只是 OHOS libc 没封装。

librtas 恰好相反：aarch64 内核没有 `rtas` syscall，**没有可 shim 的目标**。
此时任何 "shim" 都只能是编造成功路径 —— 属于 E237 `forbid_1_pattern` 禁止的行为。

> 判据一句话：**先确认目标架构内核是否存在该 syscall，存在才可 shim；
> 不存在只能如实声明。**

## 处置方案

### ① 交付判定：不裁剪、不造桩

`Makefile.am` 的 `lib_LTLIBRARIES` 全部安装，两个库都进包：

```
lib/librtas.so.2.0.0            ← 主库，aarch64 上入口必然失败（如实声明）
lib/librtasevent.so.2.0.0       ← 副库，架构中立，完全可用
include/librtas.h  librtasevent.h  librtasevent_v4.h  librtasevent_v6.h
```

### ② 如实声明（R40 / E237）

`notes.md` 单列「平台语义判定」小节写全证据链，并明确
**"编译通过 ≠ 适配完成"**，对齐 E237 禁止声称可运行的约束。

### ③ 测试分层

| 对象 | 断言内容 | 本例条数 |
|------|----------|----------|
| 副库（架构中立） | 真实功能断言 | 15 |
| 主库（他架构 syscall） | 只断言**上游文档化的失败路径** | 4（另 2 条为装载探针） |

主库的具体断言写法见姊妹条
`DRAFT-librtas-2.0.4-ohos-no-ppctree-documented-failure-assertions`。

### ④ 后续演进（不阻塞合并）

若社区确需 librtasevent 的解析能力，可另起独立包交付，保持「一个 PR 一个软件」
（W2 / JC6 原子性）。

## 避免的两种误判

- **误判 A**：当成 `env_unsupported` 止损，白白放弃可用的架构中立副库。
- **误判 B**：当成"编译通过即适配完成"，交付一个 100% 入口失效的主库（违反 R40）。

## 核验命令

```bash
# 目标架构内核是否有该 syscall（期望 0）
clang -target aarch64-linux-ohos -E -dM -x c /dev/null | grep -c __NR_rtas
# 设备树节点是否存在
ls /proc/device-tree/rtas 2>&1 || echo "MISSING: /proc/device-tree/rtas"
# 发行版架构限制
apt-cache showsrc librtas 2>/dev/null | grep -i '^Architecture'
```

## 关联

`E237`（接口缺失但主体可用）、`E245`（syscall shim 边界）、
`E007` / `E015`（config.guess/config.sub 平台识别）。
