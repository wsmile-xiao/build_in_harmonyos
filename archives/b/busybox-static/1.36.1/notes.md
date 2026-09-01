# BusyBox static 1.36.1 — 适配笔记

## 概述
BusyBox 1.36.1 (static) — statically linked multicall binary combining tiny UNIX utilities。
与 `busybox/1.36.1` 共享同一上游源码和 OHOS 兼容补丁，但通过 `CONFIG_STATIC=y` 构建完全静态链接的二进制，无运行时 .so 依赖。

## 与 busybox/1.36.1 的差异
| 项目 | busybox/1.36.1 | busybox-static/1.36.1 |
|------|----------------|----------------------|
| 链接方式 | 动态（默认） | 静态（CONFIG_STATIC=y） |
| 运行时依赖 | libc.so, libm.so 等 | 无 |
| 二进制大小 | 较小 | 较大（约 2-3 倍） |
| 适用场景 | 通用 | 嵌入式、initramfs、急救环境 |

## OHOS 适配要点
1. **HOSTCC=clang**：BusyBox Kbuild host 工具（fixdep/docproc）默认 HOSTCC=gcc，OHOS 无 gcc，配方传入 HOSTCC=clang。
2. **FEATURE_UTMP=n**：OHOS musl 未声明 setutxent/getutxent/endutxent，禁用 UTMP 及其依赖（WHO/W/USERS）。
3. **sockaddr_storage 重定义**：OHOS uapi linux/socket.h 无条件定义 struct sockaddr_storage，与 musl sys/socket.h 冲突；禁用依赖 linux/if.h / linux/netlink.h 的 applet（IP/TC/ETHER_WAKE/IFENSLAVE/MDEV/SLATTACH/IFPLUGD/UEVENT）。
4. **musl GNU 扩展缺失**：gethostid/strverscmp/sigisemptyset 经 patches/0001-ohos-compat-missing-libc-functions.patch 在 libbb/missing_syscalls.c 提供兼容实现；getusershell 依赖 /etc/shells，禁用 CONFIG_SU。
5. **sed 改 .config 后必须 make silentoldconfig** 重新生成 include/autoconf.h。
6. **package() 直接复制二进制**：make install 在 HMDFS 上创建 ~400 个符号链接极慢。
7. **CONFIG_STATIC=y**：在 `make defconfig` 之后、`make silentoldconfig` 之前注入，确保 kbuild 将 `-static` 传入链接器。

## 真机验证结果
- `conan create` 编译+链接通过（OHOS aarch64, clang 15）
- 产出 1.3MB 完全静态链接 ELF（无 NEEDED 条目）
- sign-elf 需 CI 环境证书，本机验证阶段未执行 smoke 测试

## 遇到的问题与修复
1. **OHOS /bin/sh shebang 执行拒绝**：`/bin/sh` 存在但内核拒绝作为 shebang 解释器（ELF 签名策略）。修复：批量替换源码树中所有 `#!/bin/sh` 为 bash 完整路径。
2. **Makefile/Kbuild 脚本直接调用**：BusyBox kbuild 系统直接调用脚本（不通过 $(SHELL)），导致即使 shebang 已修复，Makefile 中的脚本调用仍触发内核 shebang 解析。修复：sed 修改 Makefile 和 Kbuild.src 中所有脚本调用前缀为 `$(SHELL)`。
3. **CONFIG_STATIC sed 匹配失败**：`make defconfig` 生成 `# CONFIG_STATIC is not set` 而非 `CONFIG_STATIC=n`。修复：sed 同时匹配两种格式。
4. **llvm-ar 不在 PATH**：OHOS 工具链目录 `/data/service/hnp/bin/` 不在默认 PATH。修复：从编译器路径推导 AR/RANLIB 完整路径，同时设置 PATH。
5. **scripted_main undefined**：`CONFIG_FEATURE_SH_EMBEDDED_SCRIPTS=y` 但无嵌入脚本。修复：禁用该配置。

## 已知限制
- 禁用部分网络 applet（ip/tc/ifenslave/ether-wake/slattach/mdev/ifplugd/uevent/su）以规避 OHOS musl/头文件限制
- 禁用 FEATURE_SH_EMBEDDED_SCRIPTS（无嵌入脚本）
- 静态链接二进制体积约 1.3MB

## 上游 testsuite 情况（2026-08-31 核实更正）
此前笔记称「上游发布 tarball 不含 testsuite」，经上游仓库 `1_36_1` tag 核实为**不准确**，更正如下：

- 上游 BusyBox 1.36.1 源码树**自带** `testsuite/` 目录，含 **65 个 `*.tests` 用例文件**，
  由 `testsuite/runtest` 驱动、`testsuite/testing.sh` 提供断言框架（`make check` 执行）。
- 未纳入本配方构建的原因（非"无测试"，而是"不可移植"）：
  1. 需要 root 权限（`mount`/`mknod`/`mdev` 等用例）；
  2. 依赖可执行的 `/bin/sh` shebang 解释器，OHOS 内核 ELF 签名策略会拒绝；
  3. 大量用例覆盖本配方已裁剪的 applet（ip/tc/mdev/su/ifplugd/uevent 等）；
  4. 依赖 bash + 完整 GNU coreutils 行为，OHOS 为 musl 环境。
- 因此上游通过率为 **0/65（0%）**，改以 test_package 的 6 项 smoke 断言替代。

## test_package 统计口径（2026-08-31 修正）
原 `test.sh` 在 ELF 未签名时直接 `exit 0` 并打印 SKIP，导致「6/6（100%）」实为假通过。
现已改为逐项统计，末尾输出机器可读汇总行：

```
SUMMARY: executed=<n> passed=<n> failed=<n> skipped=<n>
```

- SKIP 表示断言**未执行**，绝不计入通过数；
- 退出码仅在出现 FAIL 时非 0，SKIP 不影响 L1 门禁；
- OHOS 未签名环境下：断言 1/2/3（存在性、静态链接、完整性）执行，断言 4/5/6 SKIP。

---

**构建验证日期**: 2026-08-28
**真机**: 10.62.220.52:2222 (OHOS aarch64, clang 15)
**最终状态**: built（conan create 通过，静态链接确认，sign-elf smoke 待 CI 环境执行）
