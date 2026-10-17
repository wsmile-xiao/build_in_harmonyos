# miniupnpd 2.3.10 适配笔记

（本文件为初稿，采信轮与上游测试完成后按实测读数补齐）

## 编译环境
- 构建系统: makefile（上游手写 `configure` + `Makefile.linux_nft`，非 autoconf）
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- 平台: HarmonyOS PC aarch64
- 状态: built

## 源码
- URL: https://github.com/miniupnp/miniupnp/releases/download/miniupnpd_2_3_10/miniupnpd-2.3.10.tar.gz
- sha256: f9c34ed3632fb60cd248dd5897bd98479a103a75688b056ca2f069e68ab32987（305458 字节）
- 三路互证: GitHub release 资产 / miniupnp.tuxfamily.org/files / miniupnp.free.fr/files
  三处 sha256 与 sha512 完全一致，且 sha512 与 Gentoo Manifest、Alpine APKBUILD 记录一致；
  上游 tag `miniupnpd_2_3_10` = b5e5d2eb069822b7f00d56c8e61033b9d500e60c（git ls-remote）。
  Conan Center Index 无 `recipes/miniupnpd`（config.yml/conanfile.py 均 404，对照 `recipes/miniupnpc` 200）。

## 编译步骤
1. `configure --host-os=Linux --host-os-version=1.12.0 --host-machine=aarch64 --firewall=nftables`
2. `make CC=<clang> -j1`（构建 miniupnpd + miniupnpdctl + TESTS=1 的 11 个测试程序）
3. `make check`（上游注册的 4 个 validate 目标）
4. 另跑 4 个上游未被 check 驱动的测试程序（见 reports/upstream-tests.md）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `Unknown OS : HarmonyOS` | 上游 OS 分支只认 BSD/Linux/Darwin/SunOS 等 `uname -s` 结果 | 走上游自带交叉分支 `--host-os=Linux --host-os-version=1.12.0 --host-machine=aarch64` |
| 2 | `[: Kernel: missing )` | `--host-os-version` 传含空格的 `HongMeng Kernel 1.12.0`，上游 KERNVER 用 `awk -F.` + `[ ]` 算术 | 传纯数字版本 `1.12.0`（真实内核版本分量） |
| 3 | `linux/socket.h:23: redefinition of 'sockaddr_storage'` | OHOS SDK 的 `<linux/netfilter.h>` 链到 `<linux/socket.h>`，与 `<sys/socket.h>` 各自定义一次 | `CPPFLAGS += -D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=sa_family_t`（与 libnftnl/1.3.1 同款，见 E119） |
| 4 | `libmnl/libmnl.h` 找不到、链接缺 nftnl_* | 未注入 `PKG_CONFIG_PATH`，上游 `pkg_detect` 回落 "no libnftnl or libmnl pkg-config found" | `generate()` 把 generators_folder 前置进 `PKG_CONFIG_PATH`，configure 的 `pkg_detect libnftnl libmnl` 命中后把 `-I/-L/-l` 写进 config.mk |
| 5 | `make check` 的 validategetifaddr 报 exit 1 | 上游 `testgetifaddr.sh` 第一步 `command -v ip \|\| exit 1`；鸿蒙 toybox 未编入 `ip` applet | 构建时用 busybox（`/data/service/hnp/bin/busybox` 自带 `ip` applet）在任务本地 bin 目录挂 `ip` 链接并前置到 PATH，**不改上游测试脚本** |
| 6 | iptables 后端编不过 | `<xtables.h>` / `<libiptc/libiptc.h>` 属 iptables 源码树，制品仓无该配方 | 改用 nftables 后端（libnftnl+libmnl 在 ohpcd 有 armv8/clang15 预编译） |

## 源码修改
无补丁（`patches_applied: []`）。全部差异由 configure 开关、CPPFLAGS 与 PATH 处理。

## 依赖版本
- libnftnl/1.3.1（传递 libmnl/1.0.5）

## 验证结果
- 上游测试：见 reports/upstream-tests.md（候选数法 **N=24** = max(被审 2.3.10 源码树 test*.c 23, 上游当前 HEAD b2b496a 的 24，HEAD 新增 testupnphttp.c/validateupnphttp)；实测 N′=8 个用例入口，四分项 PASS 7 / FAIL 0 / SKIP 1 / NOT_RUN 16 逐项归因）
- 消费者测试：见 test_package/MANIFEST.yml（**32** 条断言 = 10 条消费者断言 + 探针 22 项必检）
- 网络栈一手探针：`test_package/ohos_netprobe.c`（22 必检 + 8 能力登记）
