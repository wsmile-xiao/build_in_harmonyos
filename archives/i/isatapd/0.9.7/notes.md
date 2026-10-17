# isatapd 0.9.7 适配记录

## 概览
- 构建系统：autotools（tarball 自带生成的 configure + Makefile.in，无需 autoreconf）
- 日期：2026-09-24
- 工具链：clang/clang++（OHOS aarch64，musl）
- 交付形态：application（ISATAP 隧道守护进程；上游装到 ${sbindir}，conan AutotoolsToolchain
  以 `--sbindir=${prefix}/bin` 归一，最终包内路径为 bin/isatapd，W3 日志坐实）
- 状态：built（待 release 流水线上传制品后方可标 published）

## 上游测试情况
上游 isatapd 无任何自动化测试：三个 Makefile.am（顶层/src/man）均无 TESTS 变量，
tarball 内无 test/check 源文件，`make check` 只是 automake 生成的空目标（0 用例）。
守护进程运行时需 root 权限 + 内核 ISATAP 隧道接口（ioctl SIOCADDRTNL），
比赛 worker 用户态无 root、无内核隧道支持 → 运行时路径不可执行。
故上游静态声明 0 / 实际执行 0，功能面靠真实消费者测试（执行打包二进制）覆盖。

## 适配改动（3 处真实修改，均已构建验证）
| # | 文件 | 问题 | 修法 |
|---|------|------|------|
| 1 | configure | HMDFS 下 `umask 077 && mktemp/mkdir` 造临时目录被拒 → config.status 报 `subs1.awk: Permission denied`、`could not setup config files machinery` | 补丁去掉 `umask 077 &&`，保留真实 mktemp/mkdir（E011/E114） |
| 2 | src/tunnel.c | 内核 UAPI 头与 musl 双重冲突：①`linux/ip.h` 重复定义 `struct iphdr`；②CI worker sysroot（ohos-sdk 26.0.0.18）`linux/if.h→linux/socket.h` 裸定义 `struct sockaddr_storage/sockaddr/sa_family_t` 与 musl `sys/socket.h` 冲突（本地 sysroot 无②故 W3 未现；`_LINUX_SOCKET_H` 在该 SDK 非真实 guard 宏，CI 二轮实证无效） | ①include 前 `#define _UAPI_LINUX_IP_H 1`（CI 一轮实证有效）；②**改名护盾**：include `linux/if_tunnel.h` 期间 `#define sockaddr/sockaddr_storage/sa_family_t <改名>` 后 `#undef`，不依赖 sysroot 宏名（E091/E119 宏卫士跳头家族的 guard 不可靠变体） |
| 3 | configure（运行时）| 交叉编译下 AC_FUNC_MALLOC 误判 malloc 不可用 → 链接期 `undefined symbol: rpl_malloc` | 配方 configure_args 预热缓存 `ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes` |

另：交叉三元组显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`；
HMDFS 禁 mkfifo，递归 `make -j2` jobserver 失败 → `make -j1`。

## 手工编译验证（device，模式 B）
```
configure（含缓存预热）→ make -j1（MAKE_RC=0）→ make install DESTDIR（INSTALL_RC=0）
产物：ELF 64-bit ARM aarch64 PIE, musl 动态链接
运行面探针：
  isatapd -h  → 打印 "Usage: isatapd [OPTIONS] [ROUTER]..."，退出码 1（getopt 帮助路径）
  isatapd --help → 同上 Usage 横幅
  isatapd --no-such-xyz → "unrecognized option: no-such-xyz" + Usage，退出码 1
  isatapd -v / --version → 不识别该短选项（isatapd 无 --version），走未知选项分支
```

## 消费者测试（test_package）
`test_package/test_smoke.py`（L0c 测试源文件）执行打包后的 bin/isatapd 二进制，2 条行为断言：
1. `isatapd -h` 输出含完整 Usage 横幅（含 --name/--link/tunnel 关键字）——证明二进制成功链接且 getopt 选项解析器功能正常（非 stub）；
2. `isatapd --definitely-not-an-option` 非零退出且报 "unrecognized option"——证明参数校验真实执行。
（守护进程运行时隧道面无法在本环境执行，理由见上，不虚报。）

## 测试数字（四向同源：manifest.yaml / notes.md / MANIFEST.yml / PR 正文）
- 上游静态声明用例数：0
- 上游实际执行用例数：0（无自动化测试，`make check` 空目标）
- 条件/依赖未执行：运行时隧道路径 1 项（需 root+内核隧道，如实标注，不静默删）
- 新增消费者测试：1 个消费者程序（test_package），2 条断言

## M13 先决自检结论（诚实申报）
配送单 framing 为 M13（makefile-install-cmd-absent-makevar-override）。三先决全不成立：
- 先决①：`install` 命令来源——isatapd 是 autotools 项目，AC_PROG_INSTALL 生成
  `INSTALL = @INSTALL@`，config.status 替换为 install-sh/ginstall，非裸 Makefile 字面量 `install`；
- 先决②：构建日志中 `install: Command not found` / Error 127 出现次数 = 0；
- 先决③：不适用。
⇒ M13 不适用，本包不空走该草稿（该草稿 affected_scope 明文排除 autotools）。

## B 判定
`hit`：本包三处阻塞分别命中知识库既有条目——
- E011（edit-umask-in-configure）+ E114（bypass-mktemp）覆盖 umask/config.status；
- E091（define-guard）/ E119（macro-guard-skip-header）家族覆盖 struct iphdr 重复定义（同机制，不同结构体）；
- DRAFT-ohos-autotools-rpl-malloc 覆盖 AC_FUNC_MALLOC 交叉误判缓存预热。
无跨库新增机制 ⇒ 判 hit，不提新草稿，不建 B Issue。

## 收尾
- 依赖：无第三方 conan 依赖（纯系统 libc）。
- 风险：内核隧道运行时路径未覆盖（本环境固有限制，非配方缺陷）。
---

**编译结束**: 2026-09-24 18:26
**最终状态**: built
