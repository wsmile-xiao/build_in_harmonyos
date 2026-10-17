# paxtest 0.9.15 测试报告（OHOS PC / aarch64）

> 通过口径（安全探测类套件，无断言式测试框架）：**每个测试项运行成功并给出结果**——
> 攻击探测项输出 `Killed/Ok/Vulnerable`，随机化项输出 `N quality bits (guessed)` 或
> `No randomization`；驱动 `./paxtest kiddie|blackhat` 退出码 0。
> 本报告数据来自真机实跑（HarmonyOS PC，HarmonyOS 6.1.0.117，内核 HongMeng Kernel 1.12.0，aarch64）。
> 共享设备：跑测期间其他成员构建并行（loadavg ≈ 20）；随机化位数为采样估计（1500 次/项，
> fast 变体 25 次），用于功能验证与相对比较。

## 1. 上游测试面与统计

paxtest 上游本身即内存保护回归套件：无独立测试目录、无 ctest/pytest 注册（N_static=0 /
N_registered=0）；测试面 = **34 个测试程序** + 15 个 helper + `genpaxtest` 生成的驱动。
驱动一次运行全部测试项（`kiddie`/`blackhat` 两模式）。

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 攻击探测（exec/mprot/writetext） | 15 | execstack 族 5 + mprotect 变体 5 + 共享库 bss/data 2 + 共享库 mprotect 2 + writetext 1 |
| 随机化测量（randbody） | 13 | 每项采样 1500 次（anon/heap×2/main×2/shlib/vdso/stack×2/argv-env×2/shlibdelta×2） |
| 随机化测量（fastrandbody） | 2 | 内存耗尽场景，每项 25 次 |
| 返回攻击（RET/RETX） | 4 | rettofunc strcpy/memcpy 及 PIE 变体 |
| **合计** | **34** | 通过 = 运行成功并给出结果 |

### 适配后实际执行（真机，kiddie 与 blackhat 各一轮）

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 真机实跑并给出结果 | 31 | — | 攻击探测 15 + 随机化 12 + fast-rand 2 + rettofunc strcpy 2 |
| 语义性无输出（aarch64） | 2 | — | rettofunc memcpy / memcpy PIE：aarch64 返回地址在 x30 而非栈帧，256B 栈溢出未劫持控制流 → 子进程正常退出（§4） |
| 平台差异中止 | 1 | 0 执行 | VDSO randomization：OHOS `/proc/self/maps` 无 `[vdso]` → getvdso 无输出 → randbody 中止该行（§4） |
| **鸿蒙特有测试** | **21** | 新增 | `test_package/` 消费者断言（`conan create` 内真实执行，见 §5） |
| **合计** | **55** | | |

## 2. 实跑结果（真机原始输出：`reports/device-kiddie.log`、`reports/device-blackhat.log`）

### 攻击探测（kiddie，15/15 Killed，无一 Vulnerable）

```
Executable anonymous mapping             : Killed
Executable bss                           : Killed
Executable data                          : Killed
Executable heap                          : Killed
Executable stack                         : Killed
Executable shared library bss            : Killed
Executable shared library data           : Killed
Executable anonymous mapping (mprotect)  : Killed
Executable bss (mprotect)                : Killed
Executable data (mprotect)               : Killed
Executable heap (mprotect)               : Killed
Executable stack (mprotect)              : Killed
Executable shared library bss (mprotect) : Killed
Executable shared library data (mprotect): Killed
Writable text segments                   : Killed
```

解读：所有“把数据当代码执行”的尝试（含 mprotect 解除限制后再执行）均被内核以信号终止，
即 OHOS 未允许这些内存类被执行；writetext 的 text 段改写同样被拒绝（Killed）。
**注意**：Killed 是“攻击未成功”的结论，不等价于逐项保护的完整证明（如 NX 是否存在需结合平台声明）。

### 随机化测量（bits guessed；kiddie）

```
Anonymous mapping randomization test     : 19 quality bits (guessed)
Heap randomization test (ET_EXEC)        : 19 quality bits (guessed)
Heap randomization test (PIE)            : 19 quality bits (guessed)
Main executable randomization (ET_EXEC)  : 21 quality bits (guessed)
Main executable randomization (PIE)      : 22 quality bits (guessed)
Shared library randomization test        : 21 quality bits (guessed)
VDSO randomization test                  : ./getvdso: No error information
Stack randomization test (SEGMEXEC)      : 21 quality bits (guessed)
Stack randomization test (PAGEEXEC)      : 21 quality bits (guessed)
Arg/env randomization test (SEGMEXEC)    : 21 quality bits (guessed)
Arg/env randomization test (PAGEEXEC)    : 21 quality bits (guessed)
Offset to library randomisation (ET_EXEC): 23 quality bits (guessed)
Offset to library randomisation (ET_DYN) : 23 quality bits (guessed)
Randomization under memory exhaustion @~0: 22 bits (guessed)
Randomization under memory exhaustion @0 : 22 bits (guessed)
```

### 返回攻击（kiddie）

```
Return to function (strcpy)              : paxtest: return address contains a NULL byte.
Return to function (memcpy)              : (无输出，见 §4)
Return to function (strcpy, PIE)         : paxtest: return address contains a NULL byte.
Return to function (memcpy, PIE)         : (无输出，见 §4)
```

### blackhat 模式

`blackhat` 一轮完整运行（driver rc=0）：**攻击探测与返回攻击结果与 kiddie 一致（15/15 Killed；
rettofunc 同前）**；body 类测试每项先打印一行
`INFO: The blackhat mode not supported due to missing nested function support in clang.`
（上游对 clang 构建的实现限制，见 §4），随后按 kiddie 语义继续。
随机化项为采样估计，两轮存在正常涨落（如 Main ET_EXEC 21→22、Main PIE 22→21），
量级一致（19–23 bits）；逐行对比见 `reports/device-blackhat.log`。

### 环境与驱动备注

- 驱动输出首行 `./paxtest[70]: ./clang: inaccessible or not found`：上游 Makefile 以
  `sh genpaxtest $(CC) $(TESTS)` 生成驱动，首个参数（编译器）被带入测试列表（上游同款行为，
  `|| echo` 吞掉失败，无影响）。
- 共享设备 loadavg ≈ 20（其他成员构建并行）；随机化位数为功能验证数据，不宜跨设备严格比较。

## 3. 平台 SKIP / 差异逐项证据

| 项 | 实测输出 | 原因 |
|----|---------|------|
| VDSO randomization | `./getvdso: No error information`（randbody 中止） | OHOS `/proc/self/maps` 无 `[vdso]` 条目 → getvdso 无输出，fscanf 失败 |
| Return to function (memcpy / memcpy PIE) | 无输出行（子进程正常退出） | 探测以 256B memcpy 溢出 8B 栈缓冲；aarch64 返回地址在 x30 寄存器，未劫持控制流 |
| blackhat 语义 | INFO 行 + kiddie 语义 | `body.c` blackhat 技巧依赖 GCC 嵌套函数（clang 不支持；上游 `#ifdef __clang__` 分支） |

## 4. 适配缺陷与修复（补丁 0001–0005）

| | 内容 |
|---|---|
| 现象 1 | `make` 在 chpax-0.7/aout.c 处失败：`fatal error: 'a.out.h' file not found` |
| 根因 1 | chpax 支持 pre-ELF 的 a.out 格式（`chpax.h` 无条件 `#include <a.out.h>`）；musl 系 sysroot 无此头，aarch64 亦无 a.out 二进制 |
| 修复 1 | 补丁 0001–0004（portability）：移除 chpax 的 a.out 支持（aout.c 函数体、chpax.c 全局、chpax.h include/声明、io.c 检测分支） |
| 现象 2 | exec 系测试（可执行内存探测）在 aarch64 上无正判定能力（一律 Killed，含“可执行页”情形） |
| 根因 2 | `shellcode.h` 无 aarch64 分支，回退 x86 `RET`(0xC3)；ARM64 上该字节序列无法构成“执行后正常返回”的最小 shellcode |
| 修复 2 | 补丁 0005（portability）：增加 `__aarch64__` 分支使用 ARM64 `ret`（0xd65f03c0）→ 可执行页正常返回（Vulnerable）、不可执行页 Killed，判定语义恢复 |
| 复验 | 真机全量两模式 rc=0；攻击探测 15/15 Killed；补丁经 conan create 端到端应用（`apply_conandata_patches`） |

## 5. 消费者测试（`test_package/`，21 条断言，conan create 内执行）

- 包结构（4）：驱动 `paxtest`、`chpax`、`shlibtest.so`、上游 README 存在且可执行/可读；
- 测试程序齐备（1）：34 个测试程序全部可执行；
- 攻击探测实跑（8）：execstack、anonmap、mprotstack、writetext 各 rc=0 且结果匹配
  `(Killed|Ok)`——显式拒绝 `Vulnerable`；
- 地址 helper（4）：getamap、getstack1 各 rc=0 且输出可解析地址（`0x…`）；
- 快速随机化（2）：randexhaust1 rc=0 且给出 `N bits (guessed)` 或 `No randomization`；
- 负向对照（2）：`./paxtest` 无参数被拒绝（rc≠0）且打印 usage。

> 完整随机化块（randbody 1500 次 × 13 项）耗时较长，不在 test_package 内运行；其证据为
> `reports/device-kiddie.log` / `reports/device-blackhat.log` 的真机全量日志。

## 6. 复现命令

```sh
# 源码（官方归档端点）与校验
curl -sSL -o paxtest.tar.gz https://codeload.github.com/opensrcsec/paxtest/tar.gz/refs/tags/paxtest-0.9.15
sha256sum paxtest.tar.gz   # 51fe6c1eef8050fa73f2a8e620cf70a5a34a79d68cb22d07b941cf8e6c0677e7

# conan 构建与消费者测试（OHOS 目标）
conan create archives/p/paxtest/0.9.15 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device \
  --build=missing --user=ohpcd --channel=stable

# 真机全量实跑（包内运行目录）
cd <pkg>/bin/paxtest
./paxtest kiddie  "$TMPDIR/kiddie.log"
./paxtest blackhat "$TMPDIR/blackhat.log"
```

## 7. 环境与已知平台差异

| 现象 | 根因 | 影响 |
|------|------|------|
| `Killed` 无法区分“保护存在”与“攻击不适用” | 探测口径只报告攻击是否成功 | 结论表述为“不可利用”，需结合逐项分析（本项目已按测试族分类记录） |
| VDSO 随机化缺失 | `/proc/self/maps` 无 `[vdso]` | 该一项无数据（其余 12 项随机化正常） |
| memcpy 返回攻击无输出 | aarch64 返回地址在 x30 寄存器 | 该两项语义失效（如实记录，不计入通过率造假） |
| blackhat = kiddie + INFO | clang 无嵌套函数 | 以 kiddie 口径解读两模式 |
| 随机化位数受负载影响小但为估计值 | 采样统计（1500 次） | 功能验证/相对比较用 |
