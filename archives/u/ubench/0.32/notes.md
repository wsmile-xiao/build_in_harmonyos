# ubench 0.32 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 configure 只按 `uname` 生成 Makefile；交叉构建时配方直接编译上游 `ubench` 目标的 4 个对象）
- 编译日期: 2026-09-26
- 编译器: OHOS NDK clang 15（`/data/service/hnp/bin/clang` → `aarch64-unknown-linux-ohos-clang`）
- 目标: aarch64-linux-ohos，profile `ci/conan/profiles/ohos-aarch64`
- 状态: built（conan-verify G1/G2/G3 通过，test_package 7/7）

## 源码
- URL: https://www.ibiblio.org/pub/Linux/system/benchmark/ubench-0.32.tar.gz （ibiblio 官方 Linux 软件归档；ubench.lsm 的 Alternate-site `metalab.unc.edu/pub/Linux/system/benchmark` 即今 ibiblio，Primary-site phystech.com 已失效）
- sha256（文件面，`curl -O` 取得）: `92277fe3c1bb6bdd08b155193d6ec051ad85b8cb45ec0d5786c791abb7c3cedc`，13489 字节
- 许可: GPL-2.0-or-later（各 .c 文件头），`README` 打包到 `licenses/`
- 包内有一个 2000 年的 i386 预编译 `ubench`，配方不使用、不打包，产物全部从源码重编。

## 编译步骤

```bash
# conanfile.py build() 的等价命令（CC 取自 tools.build:compiler_executables）
for f in signals cpubench membench ubench; do
  clang -O2 -fPIE -Wall -Wno-deprecated-non-prototype -I. -c $f.c -o $f.o
done
clang -O2 -static-pie -s -o ubench signals.o cpubench.o membench.o ubench.o -lm
```

- 不运行上游 `configure`：它按宿主 `uname -m` 写 `CC=gcc` 与 `-m486 -malign-loops=2 …`（GCC/x86 专有），
  Makefile 的链接规则还会执行宿主 `strip`（x86 binutils 无法处理 aarch64 ELF）。对象清单与上游 `ubench` 目标
  (`objects = signals.o cpubench.o membench.o ubench.o`) 一致；上游 `LDFLAGS=-s -lm` 保留 `-s`，`-lm` 放到对象之后。
- `diskbench.c`/`netbench.c` 只在 `-DDISKNETYES` 时启用，上游默认不编；`utime` 是另一个 Makefile 目标（计时辅助程序），不在默认目标里，均不打包。
- `-static-pie`：ubench 只依赖 libc 和 libm。静态 PIE 保留 PIE/RELRO，不依赖 `/lib/ld-musl-aarch64.so.1`，
  同一产物可以在 CI 设备原生运行，也可以在 x86 runner 上经 qemu-aarch64 运行（先例：`cutmp3/4`、`ctpv/1.1`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cpubench.c:93` / `membench.c:83`: `use of undeclared identifier 'CLK_TCK'` | POSIX.1-2001 已删除 `CLK_TCK`，OHOS sysroot 只有 `_SC_CLK_TCK`（现代 glibc 同样不定义） | 补丁 0001/0002 改为 `sysconf(_SC_CLK_TCK)`；新知识草稿 **E6418** |
| 2 | `use of undeclared identifier 'sys_errlist'` ×5（cpubench/membench/ubench） | musl 从未导出 `sys_errlist`（glibc 2.32 起也删除了） | 补丁改为 `strerror(errno)`；已有草稿 tevent / irpas 覆盖，不重复造 |
| 3 | cpubench.c 隐式声明 `abs`/`exit` 警告 | K&R 写法，缺少 `<stdlib.h>` | 补丁 0001 补 `#include <stdlib.h>`/`<string.h>`（clang 16+ 会把它升级成 error） |
| 4 | configure/Makefile 不可用于交叉构建 | 按宿主 uname 写 gcc/x86 标志，并调用宿主 strip | 配方直接编译上游 ubench 目标的 4 个对象 |
| 5 | conan-verify G2 首次失败：`sha256 hash failed … Computed hash: c21b18a5…` | ibiblio 对 .tar.gz 回 `Content-Encoding: gzip/x-gzip`，Conan 的 requests 会解掉一层 gzip，于是算的是裸 tar 的哈希（`gunzip -c | sha256sum` = c21b18a5…） | 沿用已合并先例 `simstring/1.0`：`get()` 失败后回退 urllib（不解码）下载，`check_sha256` 仍校验文件面规范哈希；已有草稿 DRAFT-E690 覆盖，不重复造 |

## 源码修改

- `patches/0001-cpubench.c.patch`：补 `<stdlib.h>`/`<string.h>`；`CLK_TCK` → `sysconf(_SC_CLK_TCK)`；`sys_errlist[errno]` → `strerror(errno)` ×2
- `patches/0002-membench.c.patch`：`CLK_TCK` → `sysconf(_SC_CLK_TCK)`；`sys_errlist[errno]` → `strerror(errno)` ×2
- `patches/0003-ubench.c.patch`：`sys_errlist[errno]` → `strerror(errno)`

全部是可移植的 POSIX 替换，没有 `__OHOS__` 等平台宏；HPUX/AIX/SunOS 分支里的 `extern sys_errlist` 声明保持原样（在 Linux/OHOS 上不参与编译）。

## 依赖版本

无第三方依赖（只用 libc 与 libm，W0：`requirements()` 为空）。

## 上游测试清点（R51）

| 项 | 结果 |
|---|---|
| tests/ 目录数 | 0（tarball 共 18 个成员，无 test/tests 目录） |
| Makefile 测试目标 | 无（目标只有 ubench / default / install / utime / clean；无 check/test） |
| ctest/pytest/其他注册测试 | 0 |
| 上游"验证"方式 | README 给出各机型的参考分数，由人工对比 |

结论：上游无自动化测试（N=0，N′=0）。改由 test_package 做真实功能测试（见下）。

## 验证结果

conan-verify（`conan create`，profile ohos-aarch64）→ G1/G2/G3 PASS；test_package 在 x86_64 runner 上经 `qemu-aarch64` 实际执行打包产物：

```text
# archives/u/ubench/0.32/reports/conan-create.log L92-100（finish 内 conan-verify 的 conan create，原样摘录）
ok   [HarmonyOS] artefact: ELF64 AArch64, OHOS note, static PIE (no PT_INTERP)
runner: /usr/bin/qemu-aarch64
ok   bad option -> exit 1 with banner and usage
ok   -cs -> Ubench Single CPU 74624, 0.39s via sysconf(_SC_CLK_TCK), uname aarch64
ok   -ms -> Ubench Single MEM 257603, 0.40s via sysconf(_SC_CLK_TCK), uname aarch64
ok   [HarmonyOS] CLK_TCK -> sysconf(_SC_CLK_TCK) timing within 0.1-2.0s on aarch64
ok   -cms -> AVG 166407 == (75211 + 257603) / 2
ok   [HarmonyOS] RLIMIT_NOFILE=4 -> strerror(EMFILE) from musl: 'No file descriptors available'
all 7 ubench checks passed
```

W3（`reports/w3-local-ci.log` L235-243）同样 7/7 通过；分数每次运行会有波动（例如 MEM 256493、AVG 165264），test_package 不断言绝对分数。

适配后测试用例统计：

| 类别 | 数量 | 用例 |
|---|---|---|
| 上游测试 | 0 | 上游无测试 |
| 功能测试（test_ubench.py） | 4 | 错误选项；`-cs` 单次 CPU；`-ms` 单次 MEM；`-cms` AVG = (CPU+MEM)/2 |
| **鸿蒙特有测试** | **3** | ① OHOS 产物契约：ELF64 AArch64 + NDK `.note.ohos.ident`（owner `OHOS`）+ static PIE 无 PT_INTERP；② `CLK_TCK` 补丁在 OHOS libc 上的计时：`times()/sysconf(_SC_CLK_TCK)` 校准时长落在 0.1–2.0s 且 uname machine = aarch64；③ `sys_errlist` 补丁在 OHOS musl 上的错误路径：`RLIMIT_NOFILE=4` 使 `pipe()` 返回 EMFILE，输出 OHOS musl 自己的 strerror 文本 `No file descriptors available`（glibc 的文本是 `Too many open files`） |

- 执行方式：CI 设备（aarch64）原生运行；x86 runner 经 qemu-aarch64 运行。两者都没有时判失败，不会跳过。
- 完整基准（非 `-s`，3 分钟、多进程）在本机经 qemu 手工跑过一次：`ubench -c` 运行 3m03s，输出 `Ubench CPU: 147414`。它太长，所以不放进 test_package。
  注意：父进程被外部 kill 时，fork 出来的 worker 会继续运行，而且会捕获 SIGTERM（signalSetup 给 1–31 号信号都装了 handler），只能用 SIGKILL 清理。这是上游行为；test_package 只用 `-s` 与 EMFILE 早退路径，不会 fork。

## 注意事项

- 分数与宿主 CPU、qemu 翻译开销有关，test_package 只断言分数 > 0 与校准时长的量级，不断言绝对分数。
- 本机 x86 runner 执行的是交付产物本身（static PIE 经 qemu-aarch64），不是同源重链副本。
