# BusyBox 1.36.1 — 适配笔记

## 概述
BusyBox 1.36.1 — multicall binary combining tiny UNIX utilities。

## OHOS 适配要点
1. **HOSTCC=clang**：BusyBox Kbuild host 工具（fixdep/docproc）默认 HOSTCC=gcc，OHOS 无 gcc，配方传入 HOSTCC=clang。
2. **FEATURE_UTMP=n**：OHOS musl 未声明 setutxent/getutxent/endutxent，禁用 UTMP 及其依赖（WHO/W/USERS）。
3. **sockaddr_storage 重定义**：OHOS uapi linux/socket.h 无条件定义 struct sockaddr_storage，与 musl sys/socket.h 冲突；禁用依赖 linux/if.h / linux/netlink.h 的 applet（IP/TC/ETHER_WAKE/IFENSLAVE/MDEV/SLATTACH/IFPLUGD/UEVENT）。
4. **musl GNU 扩展缺失**：gethostid/strverscmp/sigisemptyset 经 patches/0001-ohos-compat-missing-libc-functions.patch 在 libbb/missing_syscalls.c 提供兼容实现；getusershell 依赖 /etc/shells，禁用 CONFIG_SU。
5. **sed 改 .config 后必须 make silentoldconfig** 重新生成 include/autoconf.h，否则 Kbuild 按旧头文件仍编译已禁 applet。
6. **package() 直接复制二进制**：make install 在 HMDFS 上创建 ~400 个符号链接极慢，改为复制 busybox multicall 二进制到 bin/。

## 构建验证
- conan create（OHOS armv8, clang 15）通过
- 签名 ELF（sign-elf）后可在 OHOS 执行
- 干净 CONAN_HOME 安装 + test_package 消费者 5/5 smoke 通过（381 applets：--help/--list/echo/true/wc）

## 已知限制
- 禁用部分网络 applet（ip/tc/ifenslave/ether-wake/slattach/mdev/ifplugd/uevent/su）以规避 OHOS musl/头文件限制
- 上游发布 tarball 不含 testsuite，使用替代 smoke 验证
---

**编译结束**: 2026-08-23 22:14
**最终状态**: built
