# rbootd 3.4 — 适配记录

> 分支: feat/rbootd-3.4
> 最后更新: 2026-10-01

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | rbootd（Remote Boot Daemon，HP 工作站网络引导守护进程） |
| 版本 | 3.4 |
| 状态 | built（待真机预检复核） |
| 构建系统 | makefile（无 configure/cmake/meson/autotools，单一多分支 Makefile） |
| 真实上游 | https://git.kernel.org/pub/scm/linux/kernel/git/deller/rbootd.git |
| 源码 URL | https://deb.debian.org/debian/pool/main/r/rbootd/rbootd_3.4.tar.xz |
| sha256 | 8a6543af25237f6553e40c47bcc42edf8d743e6d37516611e4a06973c5913225 |
| 大小 | 31584 字节（`Format: 3.0 (native)`，Debian 原生包，即作者发布渠道） |
| 依赖 | libpcap/1.10.6（`Makefile:10` `LFLAGS += -lpcap`，`defs.h:54` `#include <pcap.h>`） |
| 包类型 | application（系统守护进程 + 可执行文件，R38: 软件级 commands.json 已声明） |

## 二、上游测试套件审计（hmbs 机器证据门禁）
审计对象: 官方源码包 rbootd_3.4.tar.xz（2026-10-01 下载校验, sha256 见上）

- 顶层文件: Makefile / README / pcap.c / bpf.c / conf.c / parseconf.c /
  rbootd.c / rmpproto.c / utils.c / defs.h / rmp.h / rmp_var.h /
  pathnames.h / rbootd.8 / rbootd.service / skeleton / debian/ / etc-rbootd/
- 无 tests/、test/、spec/、t/ 目录；无 debian/tests（autopkgtest）目录；
  全树无 `TEST(`/`TEST_F`（gtest）、无 `def test_`（pytest）
- Makefile 仅定义 `rbootd` / `clean` / `all` / `install` / `rbootd.8.gz`
  目标, 无 `check` / `test` / `TESTS` / `check_PROGRAMS` 目标;
  `make check` 无规则可执行（`No rule to make target 'check'`）
- 上游是系统守护进程, 功能验证只能靠真实执行二进制完成

结论: 上游 rbootd 3.4 确实不存在测试套件, test_package/MANIFEST.yml 声明
`upstream_tests_exist: false` + 非空 `upstream_test_audit`；不虚构测试数字。
功能验证由 test_package 真实执行 rbootd 二进制完成（`rbootd -d -Z` 的
getopt 启动路径断言 + OHOS aarch64/musl ELF 身份断言 + 静态 libpcap 断言），
详见 test_package/MANIFEST.yml。

## 三、补丁清单
| 补丁 | 内容 | 类型 |
|------|------|------|
| 0001-Makefile.patch | 平台分支判定 `ifeq ($(UNAME_S),Linux)` 改为 `ifneq (,$(filter Linux HarmonyOS,$(UNAME_S)))`；HarmonyOS 上 `uname -s` 返回 "HarmonyOS"，原判据为假会落进 BSD 分支的 `.include <bsd.prog.mk>` 直接报 `missing separator`（POSIX make，无平台宏） | portability |
| 0002-defs.h.patch | ① 在 `#include "rmp.h"` 之前显式 `#include <sys/types.h>`：`rmp.h` 使用 BSD 类型 `u_int8_t/u_char/caddr_t`，glibc 的 `<sys/param.h>` 会传递提供 `sys/types.h`，OHOS/musl 的不提供；② 补 `#ifndef __P` 回退定义：BSD 原型宏 `__P()` 由 glibc 的 `<sys/cdefs.h>` 提供，OHOS/musl 未定义（无平台宏） | portability |
| 0003-rmpproto.c.patch | `filename = rindex(filepath, '/')` 改为 `strrchr(filepath, '/')`：`rindex()` 是 legacy BSD 别名，musl libc 不导出该符号，链接报 `undefined symbol: rindex`；`strrchr()` 是 ANSI/POSIX 等价函数（无平台宏） | portability |

## 四、配方要点（conanfile.py）
- Raw Makefile + libpcap 依赖: 从 `self.dependencies["libpcap"].cpp_info`
  取 includedirs/libdirs, 组装 `-I/-L`（Makefile 自带 `-lpcap`、`$(CC)`）
  （dhcpdump/1.10、cdpr/2.4 先例）
- 编译器从 `self.conf.get("tools.build:compiler_executables")` 获取（R33）,
  以 `make CC=... CFLAGS=... LDFLAGS=... -j1` 传入（R9: 单作业）
- 平台守卫 `self.settings.os in ("Linux", "OHOS")`（R32）
- package_type=application, `cpp_info.bindirs=["bin"]`, `cpp_info.libs=[]`（R38）
- build() 不调用 `make check`（上游无该目标）; MANIFEST 中
  `upstream_test_in_build: false` 如实声明
- 上游 `make install` 依赖 `install -o root -g root`，OHOS 无 `install`
  可执行（busybox 多调用未链接）, 且非 root 无法设置属主；package()
  改为直接拷贝 `rbootd`/`rbootd.8`/`etc-rbootd/rbootd.conf`/`debian/copyright`

## 五、验证记录
- 本机: 源码下载 + sha256 校验通过（8a6543af…3225, 31584 字节）；
  3 个补丁上下文行与上游原文件逐行核对一致，`patch -p1` 应用后与 `.work` 逐字节一致
- 本机真实交叉编译: clang 15（`aarch64-unknown-linux-ohos`）构建 6 个目标文件并链接
  （`-lpcap` 静态）成功, ELF e_machine=AArch64, 解释器 `/lib/ld-musl-aarch64.so.1`
- conan-verify: G1/G2/G3/G4 全 PASS（reports/conan-verify-report.md）
- W3 本地 CI 模拟: JC pass + conan create pass + test_package 3/3 + L1e 反证 pass，
  Pass rate 100%（reports/w3-local-ci.log）
- test_package（消费者视角）: 3 用例全通过，含 2 项鸿蒙特有用例（OHOS aarch64/musl ELF
  身份 + libpcap 静态链接）；上游无测试套件（0 用例），详见 reports/test-report.md
- 停在 LOCAL 门禁通过：未 commit / 未 push / 未创建 PR / 未上传制品

## 六、遗留问题
- 无已知编译阻塞；依赖 libpcap/1.10.6 需在制品仓可用（W0 检查项已在真机确认）
- `rbootd` 运行时需 root 与真实抓包网卡, test_package 仅覆盖 getopt 启动安全路径,
  不做真实抓包（需 root/网络, CI 不可复现）
- `pcap.c` 使用 Linux 专有 `<netpacket/packet.h>` + `PF_PACKET`；OHOS 下
  AF_PACKET/PF_PACKET 受限时需确认 libpcap `PCAP_LINUX` 后端的抓包行为
  （属运行期平台集成, 非编译阻塞）

## 七、构建环境发现（可复用，L1/L2 级）

> 以下为本次适配在 OHOS worker 上实测到的环境约束，配方已内建规避；供后续同类 Make 配方参考。

1. **stdin 为 socket 时编译器静默失败（关键）**：OHOS agent 把调用方 stdin 以
   **socket** 形式传给进程。经 `/bin/sh -> make -> /bin/sh` 链继承该 socket 作为 stdin 时，
   `clang` 会**静默退出 1 且不产出任何目标文件、无任何诊断输出**（`clang --version`
   都返回 1/空输出）。实测 `stdin=/dev/null` 或管道时恢复正常。
   → 配方 `build()` 以 `make ... < /dev/null > <log> 2>&1` 显式脱离三条标准流，
   并在 Python 侧回放日志；同时避免 `self.run(cwd=...)`（见下条）。
2. **`cwd=` 触发 HMDFS getcwd 问题**：向子进程传 `cwd=` 时该问题同样复现；
   统一用命令内 `cd "<dir>" && ...` 代替 `cwd=`。
3. **`uname -s` 在 HarmonyOS 返回 "HarmonyOS"**：Makefile 常见 `ifeq ($(UNAME_S),Linux)`
   会落空，必须用 `filter Linux HarmonyOS` 之类判据。
4. **musl libc 缺少 glibc/BSD 兼容面**：`__P()` 原型宏（`<sys/cdefs.h>`）、
   BSD 类型 `u_int8_t/u_char/caddr_t`（需显式 `#include <sys/types.h>`，musl 的
   `<sys/param.h>` 不传递提供）、legacy `rindex()` 均缺失/未导出。
5. **toybox 工具差异**：`/system/bin` 在 PATH 前置时，`grep` 为 toybox 版，
   **不搜索二进制文件（忽略 `-a`）**；`od -An -t c | tr -d ' \n'` 转换后按文本匹配可行。
6. **zsh here-doc 走 `TMPPREFIX`**（默认 `/tmp/zsh`，本机 `/tmp` 只读）：
   本地 CI 脚本（zsh）大量使用 here-doc，需 `export TMPPREFIX=$HOME/tmp/zsh/zsh`。
7. **finish/JC 范围**：`junk_check` 在未提交（`git diff origin/main...HEAD` 为空）时回退
   “整仓 full 扫描”，会命中 origin/main 中其他库遗留的 `.build-closed`/`.staging-verified`；
   以 PR diff（`JUNK_PR_DIFF`，等同 CI 的 pr.diff）喂入后本库 13 个文件 JC 全通过（0 junk）。
---

**编译结束**: 2026-10-01 15:00
**最终状态**: built
