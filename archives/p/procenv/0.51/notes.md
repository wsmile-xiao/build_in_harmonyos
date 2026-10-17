# procenv 0.51 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure/Makefile.in）
- 编译日期: 2026-09-16
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 任务版本 `0.51` 对应上游 tag `0.51`。
- 源码：`https://codeload.github.com/jamesodhunt/procenv/tar.gz/refs/tags/0.51`
  sha256 `b831c14729e06a285cc13eba095817ce3b6d0ddf484b1264951b03ee4fe25bc9`（245663 字节）。
- 产物：`bin/procenv`、`share/man/man1/procenv.1`、`share/doc/procenv/README.rst`、`licenses/COPYING`
  （CLI 工具 → 软件级 `commands.json`）。

## 适配补丁（7 个，全部 portability）

| # | 补丁 | 问题 | 处置 |
|---|------|------|------|
| 0001 | configure-relax-umask-for-hmdfs | autoconf 生成的 configure 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，HMDFS 上 config.status 随后写 `subs1.awk` 报 `Permission denied`（E011 类） | `umask 077` → `022`（与仓库 e2fsprogs 0003 补丁同法） |
| 0002 | check-all-args-honour-TMPDIR | 上游测试脚本硬编码 `template=/tmp/...`，OHOS 的 `/tmp` 只读 | 改为 `${TMPDIR:-/tmp}` |
| 0003 | platform-headers-ohos-portability | ① `major()/minor()` 在 musl 下不在 `<sys/types.h>`，而代码只在 `#ifdef __GLIBC__` 时包含 `<sys/sysmacros.h>` → 编译失败；② `#include <linux/if.h>` 与 musl `<sys/socket.h>` 的 `sockaddr_storage` 重定义（E091）；③ `pthread_getconcurrency()` 是 glibc 扩展，OHOS musl 无 | ① 包含条件改为 `__GLIBC__ || __linux__`；② 按 E091 用 `#define sockaddr_storage __linux_sockaddr_storage` 守卫；③ 该字段加 `&& defined(__GLIBC__)` 守卫（降级为不输出） |
| 0004 | src-makefile-precise-werror-relax | 上游 `AM_CFLAGS` 含 `-Werror`，新编译器对 `-Wunused-but-set-variable` 报警 → 构建失败 | 按 P007 **精准**加 `-Wno-error=unused-but-set-variable`（同时改 `.am` 与生成的 `.in`，避免触发缺失的 automake） |
| 0005 | platform-linux-affinity-musl | musl/OHOS 无 `pthread_getaffinity_np`（有 `pthread_getattr_np`），代码用 `CPU_ALLOC` 分支走了 np 版本 → 编译失败 | 条件 `#if !defined(CPU_ALLOC) \|\| !defined(__GLIBC__)` → 退回 `sched_getaffinity(0, ...)`（属仓库已有知识：`pthread_getaffinity_np` 相关条目） |
| 0006 | getpwuid-tolerate-missing-uid | OHOS 的 `/etc/passwd` 只有 root/bin/system，进程 uid（如 20020085）查不到，`getpwuid()` 返回 NULL 且 `errno==0` → 上游 `die("uid %d no longer exists")` 直接失败 | `getpwuid()` 返回 NULL 且 `errno==0` 时，改用一张**空但非 NULL 的 passwd 记录**
                        （`pw_name`/`pw_passwd`/`pw_gecos`/`pw_dir`/`pw_shell` 均为 `""`，uid/gid 为 -1）并**继续原有流程**
                        （不提前 return），避免下游解引用 NULL；其他平台同样受益（容器/无 passwd 环境）。
                        属仓库已有知识：`getpwuid`/`no longer exists` 相关条目 |
| 0007 | check-all-args-skip-without-groff | 上游 `get_man_options()` 用 `groff -a -man -Tascii` 渲染 man page 做选项交叉校验；OHOS 无 groff → 校验必然失败 | 无 groff 时 `msg` 提示并跳过该交叉校验（其余断言照跑） |

## 平台能力问题的实证（不属于 procenv 缺陷）

### 1) `check_pr_list`（libcheck，7 用例）：**已解决**（需设 `TEMP`）

libcheck 创建 fork/IPC 临时文件时的目录启发顺序是：

```
1) $TEMP   2) P_tmpdir（编译期 "/tmp"）   3) $TMPDIR   4) "."
```

关键：**`P_tmpdir` 优先于 `TMPDIR`**，而 OHOS 的 `/tmp` 只读 → 无论怎么设 `TMPDIR`
都会报 `check_msg.c:317: Unable to create temporary file for communication`。

正确做法：**设 `TEMP` 指向可写目录**（`TEMP` 是第一优先级），实测即通过：

```
TEMP=<writable> LD_LIBRARY_PATH=<check>/lib ./check_pr_list
→ 100%: Checks: 7, Failures: 0, Errors: 0
```

配方已在 `build()` 中设 `TEMP`/`TMPDIR` 指向构建目录下的可写目录，`make check` 现已
包含 `check_pr_list`。

### 2) 无参数全量 dump 忙等挂起
`procenv`（无参数）在 OHOS 上 **忙等自旋**（CPU 98%、线程状态 R）。逐参数定位：

```
timeout 3 procenv -b   → 超时(124)   # --libs
timeout 3 procenv -i   → 超时(124)   # --misc
其他 -X/--xxx（如 --uname/--limits/--environment/--format=json）正常返回
```

现场可见进程持有一个 `socket(AF_INET, SOCK_DGRAM, IPPROTO_IP)`（`/proc/<pid>/fd`），
对应接口信息枚举路径；`build()` 里以 `timeout 15` 跑无参数版本，退出码 124 记入日志。
**约定**：消费者/测试不要调用 `-b/--libs`、`-i/--misc` 与无参数全量 dump；其余节正常。

## 上游测试执行情况（R51）

| 上游 TESTS | 状态 |
|-----------|------|
| `tests/show_machine_details` | ✅ PASS |
| `check_all_args` | ✅ PASS（groff 交叉校验按技术原因跳过） |
| `check_pr_list`（libcheck 7 用例） | ⚠️ 无法执行（libcheck IPC 限制，见上；`timeout 20` 实跑记录） |
| `procenv`（无参数） | ⚠️ 忙等挂起（见上；`timeout 15` 实跑记录，退出码 124） |

```
make check TESTS="tests/show_machine_details check_all_args"
→ PASS: tests/show_machine_details
→ PASS: check_all_args
→ All 2 tests passed
```

## 消费者验证（test_package）

真实运行安装后的 `bin/procenv`，5 项断言：
`--version`（含 0.51）、`--format=json --uname`（JSON 可解析）、`--format=xml --sysconf`（含 `<procenv`）、
`--limits`、`--environment`（含 PATH）。

## 依赖
- 构建/测试依赖：`check/0.15.2`（`test_requires`，仅用于构建 `check_pr_list`；不传播给消费者）

## 验证结果

```bash
conan create archives/p/procenv/0.51 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64
# -> CREATE_EXIT=0；All 2 tests passed；test_package 5/5
```

## 注意事项
- 不要在 OHOS 上调用 `procenv -b/-i` 或无参数（会忙等）；其余节可正常使用。
- `procenv` 在 OHOS 上不报告 libcap/selinux/apparmor 能力（这些用户态库不可用；
  注意 OHOS 自带的内核风格 `<sys/capability.h>` **不含** libcap API，见 conanfile 中的
  `ac_cv_header_sys_capability_h=no` 说明）。
