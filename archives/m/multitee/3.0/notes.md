# multitee 3.0 适配笔记

## 编译环境
- 构建系统：上游无任何构建文件，由补丁 0001 新增最小 Makefile；配方用 `AutotoolsToolchain` + `Autotools.make()`
- 编译日期：2026-09-23
- 编译器：OHOS clang 15.0.4（`aarch64-unknown-linux-ohos`，NDK musl sysroot）
- 状态：built（conan-verify 与 W3 本地 CI 通过；PR 阶段不上传制品）
- 依赖：仅 libc（无 conan requires）

## 上游与源码来源（R39）
- multitee 3.0 的作者是 Daniel J. Bernstein，1991-10-21 发布于 alt.sources，public domain。
  作者站点仍提供原帖 `https://cr.yp.to/software/multitee-3.0.shar.gz`（sha256 `175aece60e9cd7d9645e606ebf654e81b1612e8af8dac3bf18a3be966a42e34f`）。
- shar 本身是 shell 脚本，conan `get()` 解不开；让配方执行下载来的脚本也不可取。因此配方使用任务指定的上游仓库
  `salsa.debian.org/debian/multitee` 的 `upstream/3.0` tag 归档，sha256 为 `76371d9a257f2113b28ae181b99bfabd3d5d22f1ebd5bd81625de4633361b751`。
  该 tag 是原始发布的导入，不含 debian/ 目录。
- 等价性核验：用 Python 按 `sed "s/^X//" >'文件' <<'END_OF_FILE'` 的结构解析 shar（只解析，不执行），得到 20 个成员，
  与 tag 归档解包结果 `diff -r` 逐字节一致。归档包间隔约 40 分钟下载两次，sha256 相同（GitLab 按需生成的包是稳定的）。
- 没有使用任何 Debian 补丁。Debian 的 `compile.patch` / `warnings-and-sigvec.patch`（属 debian/*，GPL-2+）只用来对照思路，
  补丁 0001–0005 都是本次独立编写的。

## W0 / W0b / 语言预检
- W0：没有 conan 依赖（只用 libc，由 OHOS sysroot 的 musl 提供），不需要 `conan download`。
- W0b：仓库里没有 multitee 历史归档；上游仓库也没有同名分支或 PR（`list-prs --state all --source-branch feat/multitee-3.0` 结果为 0 条）。
- lang-preflight：detected=c（8 个 .c，主体占比 100%），与任务的 cpp 同属一族，通过。

## 编译步骤
1. `source()`：`get()` 解包 upstream/3.0 归档，`strip_root`。
2. `generate()`：`AutotoolsToolchain` 写出构建环境，内容为 `CC=/data/service/hnp/bin/clang`、`CFLAGS=-O3`、`CPPFLAGS=-DNDEBUG`（R33：编译器和标志都来自 Conan）。
3. `build()`：`apply_conandata_patches()` 应用 0001–0005，然后在源码目录执行 `make multitee -j1`（E074：OHOS worker 上 HMDFS jobserver 会报 EPERM）。
4. `package()`：`bin/multitee`、`share/man/man1/multitee.1`，以及 `licenses/LICENSE`。上游没有单独的许可证文件，LICENSE 取自 multitee.c 头注释里的 public domain 声明。
5. 不构建上游附带的 `tee.c`（基于 multitee 的 tee 克隆）。Debian 同样不发布它，而且包里带一个 `tee` 会遮蔽 PATH 上的系统 tee。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游没有 Makefile 或任何构建文件 | 1991 年的 shar 发布只含源码和手册 | 0001 新增最小 Makefile，规则只引用 `CC/CPPFLAGS/CFLAGS/LDFLAGS/LDLIBS` |
| 2 | `sigdfl.c:30`、`sigsched.c:365` 报 `variable has incomplete type 'struct sigvec'`；`sigvec/sigblock/sigsetmask/sigmask` 为隐式声明 | 4.2BSD 信号接口从未进入 POSIX，musl 不提供（知识草稿 E634） | 0004/0005 逐点改写为 `sigaction/sigprocmask/sigset_t`，不加平台宏 |
| 3 | `ralloc.c` 报 `incompatible redeclaration of library function 'malloc'`，`_exit` 为隐式声明 | 前 ANSI 的 `extern char *malloc(); extern void free();` 与 libc 原型冲突，size 参数也不经 size_t 转换 | 0003 删除旧声明，改为 include `<stdlib.h>`/`<unistd.h>` |
| 4 | `multitee.c` 的 `read/write/exit/perror` 为隐式声明 | 1991 年的代码没有 include 标准头；LP64 下 `ssize_t` 返回值会按 int 截断 | 0002 补 `<stdio.h>/<stdlib.h>/<unistd.h>` |
| 5 | x86_64 runner 上 test_package 执行产物时报 `aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1'` | 宿主没有 OHOS musl loader，动态产物在进入 main 前就失败（知识草稿 E635） | 本地功能验证改用同源 .o 静态重链后在 qemu 下运行；test_package 在该宿主上显式报 SKIPPED，在 aarch64 CI 上强制执行 |

## 源码修改（补丁清单，均由 `refresh-patch --auto` 生成）
- `0001-Makefile.patch`（+17）：新增 Makefile，`OBJS = multitee.o sigsched.o sigdfl.o ralloc.o getopt.o fmt.o scan.o`。
- `0002-multitee.c.patch`（+3）：`#include <stdio.h> <stdlib.h> <unistd.h>`，放在 getopt.h 之前。getopt.h 会用宏把 getopt/optarg 改名为作者自带的实现，因此不会和 libc 冲突。
- `0003-ralloc.c.patch`（+2/−2）：用 `#include <stdlib.h> <unistd.h>` 替换 `extern char *malloc(); extern void free();`。
- `0004-sigdfl.c.patch`（+29/−21）：`sigdfl()` 改为 `sigaction(SIG_DFL)` + `kill(getpid())` + `sigprocmask(SIG_SETMASK, 全集−{sig,SIGCONT})` + 恢复原 handler 与掩码，语义与原实现一一对应。
  SIGCONT handler 签名改为 `void (*)(int)`；它置位的 `cont` 改为 `volatile sig_atomic_t`，因为 `-O3` 下对普通 int 的 `while (!cont);` 会被优化成死循环。
- `0005-sigsched.c.patch`（+13/−15）：`typedef int sigc_set` 改为 `sigset_t`，`sigc_*` 宏映射到 `sigismember()==1 / sigaddset / sigemptyset / sigprocmask`（作者当年已在注释里写出这组 POSIX 等价调用）；`ss_exec()` 改用 `sigaction()` 安装调度器的信号 handler。
- `sa_flags = 0` 的取舍：严格说，4.2/4.3BSD 的 `sigvec` 在 `sv_flags` 不带 `SV_INTERRUPT` 时会自动重启被中断的慢速系统调用，
  对应的是 `SA_RESTART`。这里仍取 0，原因有两点：
  - sigsched 只在 `select()` 前后解除阻塞（`sigc_unblock` → `select` → `sigc_block`），而 Linux 上 `select()` 无论是否设 `SA_RESTART` 都不会重启，代码本身按 `EINTR` 处理；
  - `sigdfl()` 解除阻塞的窗口里只有不含系统调用的忙等。
  因此两处 handler 都不会打断可重启的调用，两种取值行为一致。
- 补丁里没有 `__OHOS__` 或其他平台宏，全部是 POSIX 写法，在 glibc/BSD 上同样成立。
- 有意保留、未改的上游告警：K&R 函数定义（`-Wdeprecated-non-prototype`）、隐式 int 的 `main`、悬空 else 和"赋值作条件"一类风格告警，以及 `multitee.c:186` 的指针类型混用（转换前后值不变，无害）。这些与移植无关，为保持补丁最小没有动。
- 已知上游缺陷（未修复）：Debian #716121。`e` 链接指向一个没有作为输入声明的超大 fd 编号时会越界，例如 `'e11800802)'`。正常用法（e 指向已声明的输入 fd）不受影响，本次测试也没有覆盖这种畸形输入。

## 依赖版本
- 无 conan 依赖；运行期只依赖 OHOS 系统 musl `libc.so`（`NEEDED: libc.so`）。

## R51 上游测试清点（N=0）
- 归档包共 20 个文件：8 个 .c（multitee tee sigsched sigdfl ralloc getopt fmt scan）、8 个 .h（含 `config/fdsettrouble.h`）、4 份手册（multitee.1 tee.1 sigsched.3 sigdfl.3）。没有 tests/ 目录、没有测试源码或数据，也没有 Makefile，因此不存在 check/test 目标。
- 作者的 shar 是同样的 20 个成员，封面文字只给了用法示例。
- Debian 没有 `debian/tests`（无 autopkgtest），`debian/rules` 只有 `dh $@`。
- 结论：上游用例 N=0，可运行 N′=0，也就不存在上游测试的修改或豁免。功能覆盖由 test_package 补全（见下）。

## 验证结果

```text
conan-verify           : PASS（G0/G1/G2/G3）；G4 工具记 PASS，但未取到 package id、实际未执行，L2/L4/L5 同因跳过；
                         产物属性另行人工核对如下（并由 test_package A1-A4 覆盖）
产物                   : ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1
                         NEEDED libc.so；FLAGS BIND_NOW；FLAGS_1 NOW PIE；GNU_RELRO 存在；GNU_STACK RW（栈不可执行）；无 RPATH/RUNPATH
包内容                 : bin/multitee, share/man/man1/multitee.1, licenses/LICENSE
test_package（x86_64） : A1-A4 制品检查 4/4 通过；F1-F11 功能层显示 SKIPPED（宿主无法加载 aarch64 OHOS 镜像）——不计为通过
本地功能实跑           : 取 conan 构建目录中与交付产物同源的 7 个 .o（交付产物与构建目录产物 sha256 均为 f904a5bf…），
                         用 OHOS clang -static 链接 NDK libc.a 重新生成，在 binfmt/qemu-aarch64 下跑 F1-F11：11/11 通过
W3 本地 CI（finish）   : 通过 — L0 pass / L1 pass（test_package 已执行）/ L1e 反向验证 pass / L4 pass / L5 pass /
                         JC incremental pass / KC pass；L2 skip（非阻塞：x86_64 runner 无法启动 aarch64 OHOS 动态产物）；.ci-result.json exit_code=0
```

局限：静态副本不经过动态 loader，qemu-user 用的是宿主 Linux 内核。所以这一项**不等于交付的动态产物已在 OHOS 上实跑**。交付产物的 F1–F11 由 aarch64 OHOS CI worker 上的 test_package 执行。

### test_package 用例（`test_package/test_multitee.py`）
- A1–A4（鸿蒙特有制品检查）：ELF64 LE + EM_AARCH64、PIE（ET_DYN）、`PT_INTERP=/lib/ld-musl-aarch64.so.1`、可执行位。
- F1 管道 stdin→stdout 逐字节复制；F2 200 KiB 扇出到 3 个描述符（等价于 tee）；F3 `-b 7` 小缓冲处理 20 KiB；F4 两路输入合并，每路数据块完整；
  F5 仍打开的输入会被持续服务，关闭后才退出；F6 `e` 链接：fd 0 到 EOF 时，仍打开的管道一并视为 EOF；F7 `-` 输出遇 EPIPE 只告警，其余输出完整；
  F8 `:` 输出遇 EPIPE 时进程死于 SIGPIPE；F9 `-q` 下 stderr 为空；F10 未知选项退出码为 1 且有诊断信息；F11 无参数时退出码 0、无输出。
- F7/F8 是补丁 0004/0005 的回归测试：F7 验证 sigsched 用 `sigaction()` 装上的 SIGPIPE handler，F8 验证 `sigdfl()` 的 `sigaction(SIG_DFL)+kill+sigprocmask` 路径。
- 二进制只从被测包里找，不回退到 PATH；二进制缺失会直接失败，CI L1e 反向验证依然有效。

## 注意事项
- L2 冒烟调用的是 `--version`，但 multitee 没有这个选项。上游 getopt 把以 `--` 开头的参数当作选项终止符，此时没有剩余参数，于是 `exit(0)`。所以 L2 即使显示通过，也只是退出码巧合，并没有版本输出。
- `commands.json` 按 R38/PF8 放在软件级目录 `archives/m/multitee/commands.json`，这与 PF9"archives 变更必须全部落在 包/版本 目录"冲突。建 PR 时本地实跑 PF 闸，确认 PF9 是唯一命中后，在 PR 中登记处理。
---

**编译结束**: 2026-09-23 09:20
**最终状态**: built
