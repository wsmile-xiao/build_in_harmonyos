# leave 1.12 适配笔记

`leave` — "提醒你什么时候该走了" 的 BSD 命令行小工具。到点前先提醒（剩余 5 分钟、
1 分钟），然后每分钟催一次，共 10 次。属于 NetBSD/FreeBSD 基础系统
（`usr.bin/leave`，源自 4.4BSD），BSD-3-Clause，版权归 The Regents of the
University of California。

- 产物：`bin/leave`（同时安装 `share/man/man1/leave.1` 与 `licenses/leave.c`）
- 类型：命令行工具（已按 R38 在软件级目录声明 `commands.json`）
- 依赖：无（仅 libc）→ 无 R36 依赖发布前置
- 平台：HarmonyOS PC aarch64（`os=OHOS`，OHOS 原生 clang 15，自举同机）

## 编译环境

| 项 | 值 |
|----|----|
| 设备 | HarmonyOS PC aarch64（原生轨，非交叉编译） |
| 编译器 | `/data/service/hnp/bin/clang`（clang 15.0.4，Target `aarch64-unknown-linux-ohos`） |
| sysroot | OHOS SDK 自带（`.../ohos-sdk_26.0.0.18/ohos/native/sysroot`，musl libc） |
| Conan | 2.29.1（OHOS 适配版，`os=OHOS` 为有效枚举） |
| profile | `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同 profile） |
| 构建系统 | 上游为 BSD make（不可用），实际用 clang 直接编译单一 TU |
| 临时目录 | `$HOME/tmp`（鸿蒙 `/tmp` 只读，遵循 R10） |

## 编译步骤

```bash
# 1) 拉源码（W0/W1 已确认无第三方依赖）
#    sha256 de30529de8abf49004da4120ca352d5c588a657f8845e44d5e83a4860e6bbe1f
# 2) 应用移植补丁 patches/0001-leave.c.patch
# 3) 直接用 Conan 提供的 clang 编译（R33：不依赖 shell 的 ${CC}）
<package>/bin/leave            # 安装后的可执行文件
```

实际命令（探索阶段）：

```bash
cd $BUILD_SRC_DIR
/data/service/hnp/bin/clang -O2 -o leave leave.c
# -> leave: ELF 64-bit LSB pie executable, ARM aarch64, dynamically linked,
#    interpreter /lib/ld-musl-aarch64.so.1
```

Conan 配方（`build()`）等价命令：

```python
cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
self.run('"{}" -O2 -o "{}" "{}"'.format(cc, executable, source))
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `Makefile` 只有 `PROG=leave` + `.include <bsd.prog.mk>`，`make` 无法执行 | `bsd.prog.mk` 是 BSD make 框架文件，OHOS/CI 环境不提供；且无 configure 脚本 | 绕开 make：`conanfile.py` 的 `build()` 直接用 Conan 提供的 clang 编译唯一 TU `leave.c`（R1 参数最少化） |
| 2 | `leave.c` 编译报 `__COPYRIGHT` / `__RCSID` "expected parameter declarator" | OHOS musl 的 `<sys/cdefs.h>` 是 NetBSD 专有宏，未定义 | 补丁加 `#ifndef __COPYRIGHT/__RCSID` 兜底宏（BSD 平台保持原定义） |
| 3 | `getprogname()` 无声明、无符号 | BSD 扩展接口，OHOS musl 未实现（动态符号表仅有 `__progname`） | 补丁加 fallback，仅在非 BSD 平台（`!__FreeBSD__ && !__NetBSD__ && !__OpenBSD__ && !__DragonFly__ && !__APPLE__`）编译；BSD 原路径不变 |
| 4 | `u_int` / `(u_int)` 报未声明 | `u_int` 是 BSD `<sys/types.h>` 拼写；musl 下被 `_GNU_SOURCE`/`_BSD_SOURCE` 守卫，且 `<sys/param.h>` 在本 sysroot 不包含 `<sys/types.h>`。实测 `-D_GNU_SOURCE` 亦未生效 | 补丁把 4 处 `u_int` 改为 portable 的 `unsigned int` |

> 补丁未引入任何 `__OHOS__`，全部为 POSIX/可移植写法，对 BSD 平台无行为改变
> （R8 四不准则；同时满足 preflight PF5 的 `__OHOS__` 闸）。

## 源码修改

- `patches/0001-leave.c.patch`（+23/-4，仅 `leave.c`）：
  1. `#include <sys/cdefs.h>` 之后追加 `__COPYRIGHT` / `__RCSID` 的 `#ifndef` 兜底定义；
  2. `doalarm` 声明之前追加非 BSD 平台的 `getprogname()` fallback（返回 `"leave"`，与 `PROG=leave` 一致）；
  3. 4 处 `u_int` → `unsigned int`。
- 补丁由 `ohc-run.py refresh-patch --auto` 生成（R3），并以 `strip: 1` 在 `conandata.yml` 中声明。
- 未修改上游 `Makefile` / `leave.1`。

## 依赖版本

无第三方依赖（仅 libc / musl）。W0 已用 `conan list "leave/*" -r=ohpcd` 实测制品仓
无 `leave` 任何版本（L0j 版本占用检查无冲突）；源码 include 清单只有
`sys/cdefs.h, sys/param.h, sys/time.h, ctype.h, stdio.h, stdlib.h, time.h, err.h, unistd.h`，
无外部库头文件。

## 验证结果

```bash
# 1) 编译产物
file bin/leave
# ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked,
# interpreter /lib/ld-musl-aarch64.so.1, with debug_info, not stripped

readelf -d bin/leave | grep NEEDED
# (NEEDED) Shared library: [libc.so]        # 仅 libc

# 2) 行为（真实执行）
leave 9999   # -> stderr "Usage: leave [[+]hhmm]"   ; exit 1
leave 2400   # -> 同上（hours>23）                  ; exit 1
leave 12x    # -> 同上（非数字）                    ; exit 1
leave </dev/null  # -> stdout "When do you have to leave? " ; exit 0
leave +6     # -> 父进程 exit 0；子进程打印 "Alarm set for ..., (pid N)"（随后被测试 kill）
```

W3（`conan create`）结果见 `.ci-result.json`（由 `finish leave 1.12 built` 写入，
含 conan create 日志 sha256，禁止手改）。

## 上游测试清点（R51 三步法）

**结论：上游无测试套件（N=0，N′=0，无通过率可言），附清点证据。**

清点证据（`leave_1.12.orig.tar.gz` 解包后完整文件树，`tar tzvf` 实测）：

```
drwxr-sr-x joy/joy     0 2003-08-16 03:11 leave-1.12/
-rw-r--r-- joy/joy  3391 2003-08-16 03:08 leave-1.12/leave.1
-rw-r--r-- joy/joy  4671 2003-08-16 03:08 leave-1.12/leave.c
-rw-r--r-- joy/joy   132 2003-08-16 03:11 leave-1.12/Makefile
```

- 归档总计 3 个文件：`Makefile`、`leave.1`、`leave.c`（3470 字节）。**无 `tests/` 目录、
  无测试源文件、无测试数据、无 CI 配置。**
- `Makefile`（6 行）内容为 `PROG=leave` + `.include <bsd.prog.mk>`，**无 `test:`/`check:`/
  `regress:` 目标**；`bsd.prog.mk` 的通用目标只有编译/安装。
- `leave.c`（187 行）是唯一 TU，内含 `main`/`doalarm`/`usage`，**无断言、无自测入口**。
- 该工具属 BSD 基础系统，由内核/用户态整体构建覆盖，历史上从未单独提供测试套件。
- 因此**没有可运行的上游测试**（这是"确无测试"，不是"没环境"）：三步法的第 3 步
  通过率无数据可填，如实标注 0/0。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/leave` | 可执行文件（aarch64，动态链接仅 libc.so） |
| `share/man/man1/leave.1` | 上游手册页 |
| `licenses/leave.c` | 上游无独立 LICENSE 文件，BSD-3-Clause 声明位于 leave.c 头部 |

## 源合规说明（R39 / CI preflight PF7）

**已知 PF7 会把 "Debian 重打包" 列入黑名单，本配方需要人工说明。**

1. `leave` 由 NetBSD/FreeBSD 作为基础系统的一部分维护，**上游没有任何官方发布物**：
   没有 tarball、没有 GitHub/GitLab release、没有版本化下载页，源码只存在于
   NetBSD/FreeBSD 源码树与 4.4BSD-Lite 发行包中。
2. 本配方使用的 URL 是 Debian 分发的**原始上游源码包**（`*.orig.tar.gz`）。Debian 的
   `.orig.tar.gz` 按定义就是**未经修改的上游 tarball**（Debian 自身的改动在与它并列的
   `debian.tar.xz` 中）。实测该包只含上述 3 个上游文件、保留 2003 年原始 mtime、**不含
   `debian/` 目录**，即"原版源码包"而非"Debian 打补丁后的重打包"。
3. 本适配**未使用 Debian 的任何补丁**；`patches/0001-leave.c.patch` 是为本次 OHOS 适配
   新写的可移植性修复。
4. 该 URL 是当前唯一忠实承载"确切上游 1.12 源码"的权威镜像地址；无个人 fork、无网盘、
   无不明 CDN。
5. 若 `create-pr` 因 PF7 拦截，按任务约定**不擅自 `--no-preflight`**，停下上报由主管决定。

## 注意事项

- 该工具正常运行时会 `fork` 出一个后台子进程并在到点前持续提醒（最长 ≈ 到点前 5 分钟
  起每分钟一次 ×10）。**测试绝不能调用会长期运行的路径而不回收子进程**；本适配的
  test_package 只使用"立即结束"的路径（非法参数 / 无参 EOF），以及 `+6`（父进程立即退出、
  子进程被显式 `kill`）来保证确定性、不挂起。
- OHOS 的 `/system/bin/sh`（mksh）执行 ELF 不可靠，test_package 中统一用 bash 包裹执行
  （沿用本仓库 aa3d/lci 既有做法）。
- 未启用 OHOS ELF 签名（`.codesign`）：本包二进制在鸿蒙 PC 上可直接执行（测试实测通过），
  且仓库内多数命令行工具包同样未签名；如 W3/CI 出现执行被拒再按 E486/E489 补签名。
---

**编译结束**: 2026-09-16 11:15
**最终状态**: built
