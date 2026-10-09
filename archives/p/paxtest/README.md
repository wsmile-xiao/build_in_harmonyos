# paxtest

paxtest 0.9.15 —— PaX/GrSecurity 内存保护回归测试套件（Peter Busser 开发，Brad Spengler 维护；
现官方仓库 [opensrcsec/paxtest](https://github.com/opensrcsec/paxtest)）。

它针对运行中的内核探测**进程内存保护**与**地址空间随机化**两类能力：

- **可执行内存探测（15 项）**：把 shellcode 写入各类可写内存（匿名映射、bss、data、heap、
  stack、共享库 bss/data）后尝试执行，并在 mprotect 变体中先尝试打开 `PROT_EXEC`；
  另含 writetext（改写 text 段）。
- **返回攻击探测（4 项）**：return-to-function（strcpy/memcpy，含 PIE 变体）。
- **随机化质量测量（15 项）**：对匿名映射、heap（ET_EXEC/PIE）、主程序（ET_EXEC/PIE）、
  共享库、vDSO、栈（SEGMEXEC/PAGEEXEC）、argv/env、内存耗尽场景分别采样 1500 次
  （fast 变体 25 次），给出“N quality bits (guessed)”或“No randomization”。

每项攻击探测输出 `Vulnerable`（攻击成功）/ `Killed`（进程被信号终止）/ `Ok`。

## 功能概述

- 测试程序 34 个（exec 5 + mprot 5 + shlib 2 + mprotsh 3 + rand 13 + fast-rand 2 + ret 2 + retx 2）
  与辅助程序 15 个（getamap/getheap/getmain/getshlib/getvdso/getstack/getarg/getexhaust 系）
- 驱动 `paxtest`（由 `genpaxtest` 生成）：`./paxtest kiddie|blackhat [logfile]`
- 自带 `chpax` 0.7（PaX 标志工具；OHOS 内核无 PaX 标志，运行时为无害 no-op）

## 使用方法（OHOS）

包内 `bin/paxtest` 为完整运行目录（已编译产物；驱动按相对路径解析测试程序，因此**必须
先 cd 到该目录**再执行）：

```sh
cp -a <conan包>/bin/paxtest "$TMPDIR/paxtest"      # 复制到可写目录（保留权限）
cd "$TMPDIR/paxtest"
./paxtest kiddie "$TMPDIR/kiddie.log"              # 受限模式（推荐）
./paxtest blackhat "$TMPDIR/blackhat.log"          # blackhat 模式（clang 构建见下）
```

单测程序也可独立运行（`PAXTEST_MODE=0|1` 控制模式，默认 1）：

```sh
PAXTEST_MODE=0 ./execstack        # Executable stack: Killed|Ok|Vulnerable
PAXTEST_MODE=0 ./mprotstack       # mprotect 变体
PAXTEST_MODE=0 ./getamap          # 打印匿名映射地址（随机化取样）
```

## OHOS 适配要点（aarch64 / HarmonyOS PC）

- **构建逻辑零改动**：`make -f Makefile.psm CC=<clang> LD=<ld>`（编译器/链接器取自 Conan
  `tools.build:compiler_executables`）。探针在 aarch64 上自然退化：`THEARCH` 为空
  （无 `-m32/-m64`），`-msecure-plt`/`-ftrampolines` 不被接受即丢弃，`LD_PIE` 探测按
  构建机 `ld` 的 pie 支持取值。
- **portability 补丁 0001–0004**：chpax-0.7 移除 a.out（pre-ELF）支持——musl 系 sysroot
  无 `<a.out.h>` 且 aarch64 不存在 a.out 二进制。chpax 在 OHOS 上为惰性工具（内核无 PaX
  标志；上游架构列表不含 EM_AARCH64），`paxbin` 调用失败被 `||:` 吞掉，不影响测试语义。
- **portability 补丁 0005**：`shellcode.h` 增加 `__aarch64__` 分支（ARM64 `ret`，
  0xd65f03c0）。上游无该分支时回退到 x86 `RET`(0xC3)：在 ARM64 上“可执行页”与
  “不可执行页”都会以信号终止（Killed），exec 系测试失去正判定能力。
- **blackhat 模式**：上游 `body.c` 使用 GCC 嵌套函数 trampoline；clang 构建下
  `paxtest blackhat` 打印 `INFO: The blackhat mode not supported due to missing nested
  function support in clang.` 后按 kiddie 语义继续（上游实现限制，两模式均完整运行）。
- **结果解读**：`Killed` = 攻击尝试被信号终止（目标内存不可执行/不可写）；`Vulnerable`
  = 攻击代码实际执行成功（保护缺失）；随机化项输出可重复采样的“quality bits”。
  组合结论（本设备实测）见 `reports/test-report.md`。

## 依赖关系

- **运行依赖**：POSIX sh（驱动）、libc（binaries 动态链接 OHOS musl/linker）、`uname`（驱动记录
  内核信息）。无第三方库。
- **构建依赖**：GNU make + clang（OHOS SDK）。无第三方库。

## 许可证

GPL-2.0-or-later（上游 `COPYING` 为 GPLv2 全文；`README` 声明 “version 2 or later”）。
许可证随包安装到 `licenses/COPYING`。

## 参考资料

- 上游仓库：https://github.com/opensrcsec/paxtest（tag `paxtest-0.9.15`）
- 上游站点（历史版本）：https://pax.grsecurity.net/
- 适配归档：`archives/p/paxtest/0.9.15/`（含 `reports/test-report.md` 真机证据）
