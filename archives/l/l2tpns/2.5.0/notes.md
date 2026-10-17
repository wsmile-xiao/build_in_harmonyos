# l2tpns 2.5.0 适配笔记

## 编译环境
- 构建系统: makefile（手写 Makefile，无 configure / CMake / meson）
- 编译器: clang（真机 `/data/service/hnp/bin/clang`，经 profile conf 注入、配方回退解析）
- 依赖: libcli/1.10.7（ohpcd 制品仓预编译静态包，R35 已验证在仓）

## 上游信息
- 上游仓库: https://code.ffdn.org/l2tpns/l2tpns（cgit）
- 上游版本: 2.5.0 = commit 372e5c0d29de77f5958fd55b81801f58e9eb52e0
- 源码包: `https://deb.debian.org/debian/pool/main/l/l2tpns/l2tpns_2.5.0.orig.tar.gz`
- sha256: `6b022b2e36642e676b16f8f2cccff3c199acb307e56bca09cb6e9c6fb0964e18`
  （2026-09-23 真机下载实测；与 Debian .dsc 一致；tarball 顶层目录为
  `l2tpns-2.5.0-372e5c0d29de77f5958fd55b81801f58e9eb52e0`，即上游
  `git archive` 未重打包产物）
- 归档固定理由: 官方归档 URL
  `https://code.ffdn.org/l2tpns/l2tpns/archive/372e5c0d...tar.gz` 从调查网络
  （3x60s 超时）与鸿蒙真机（curl 20s 超时，2026-09-23）均不可达，按
  implement-policy 固定到 Debian orig 并在此记录证据链。
- 许可证: GPL-2.0-only（COPYING）

## 上游测试审计（结论：上游无测试套件，NO_UPSTREAM_TESTS）
- 根 Makefile：目标仅 `all/programs/plugins/doc/clean/depend/install/dist`，
  无 `check`/`test` 目标；`all = programs plugins doc`，`doc` 递归 docs/
  （docs/Makefile 在 pandoc 缺失时 `all:` 为空目标，纯 no-op）。
- `.gitlab-ci.yml`：唯一构建步骤 `bash scripts/ci-test.sh`。
- `scripts/ci-test.sh`：`make install`（需 root、写系统路径）→
  `/usr/sbin/l2tpns -v || true`（注意 `|| true`）→ 从 `/var/log/l2tpns`
  （syslog）grep 版本与 git tag 比对。该断言需要真实启动守护进程
  （root + /dev/net/tun + 内核 L2TP）；真机实测内核 L2TP 缺失
  （`/proc/net/protocols` 无 l2tp 条目、`/proc/net/genetlink` 不存在），
  该探测路径在真机不可达。
- `test/`：bounce.c、generateload.c、radius.c（独立 test/Makefile）与
  ping-sweep —— 负载模拟工具，根 Makefile 从不递归 test/，且需真实
  LNS/LAC 拓扑才可运行，非自动化测试。
- 证据路径（归档内）：`Makefile`、`.gitlab-ci.yml`、`scripts/ci-test.sh`、
  `test/Makefile`、`test/README`、`docs/Makefile`。

## 编译步骤

```bash
make all -j1 \
  CC=<conan clang> \
  "INCLUDES=-I. -I<libcli>/include" \
  "LDFLAGS=-L<libcli>/lib" \
  "l2tpns.LIBS=<libcli>/lib/libcli.a" \
  "EXTRA_CFLAGS=-include ohos_compat.h"
```

产物拷贝（`package()`，绝不执行 `make install` —— 上游 install 硬编码
`install -c -D -o root -g root`、gzip manpage、`mknod /dev/net/tun`，E108）：
- `l2tpns`（守护进程）、`nsctl`（控制工具）→ `bin/`
- 8 个 CLI 插件 `*.so` → `lib/l2tpns/`（守护进程按编译期内置
  PLUGINDIR=`/usr/lib/l2tpns` 在运行期 dlopen；交付布局独立于部署路径）
- `COPYING` → `licenses/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cli.c`/`cluster.c` 报 `F_GETFL/F_SETFL/O_NONBLOCK/O_DIRECTORY` 未声明 | glibc 的 `<sys/file.h>` 会透传 fcntl 声明，musl 不会；两文件只包含了 `<sys/file.h>` | patch 0002：在 `#include <sys/file.h>` 后补 `#include <fcntl.h>`（最小可解释） |
| 2 | `linux/sysinfo.h` 与 `sys/sysinfo.h` 重复定义 `struct sysinfo`；`linux/socket.h` 与 `sys/socket.h` 重复定义 `sockaddr_storage`；`linux/if_ether.h` 与 `netinet/if_ether.h` 重复定义 `struct ethhdr` | OHOS SDK 的净化版 uapi 头 include guard 与 musl 不互斥（E119 家族，batctl 同根因）；l2tpns.c 同时包含 musl 头与 `linux/netlink.h`/`rtnetlink.h`/`genetlink.h`/`l2tp.h`/`if_pppox.h` | patch 0004 新增 `ohos_compat.h`：预定义 `_UAPI_LINUX_SOCKET_H`、`_LINUX_SYSINFO_H` 跳过重复块，`__UAPI_DEF_ETHHDR 0` 用净化头自带的 libc-compat 开关仅去掉重复 struct、保留 `ETH_P_*`；并补 `__kernel_sa_family_t` typedef（被 netlink/rtnetlink/pppox/l2tp 头引用）。经 `EXTRA_CFLAGS=-include` 注入每个 TU |
| 3 | `linux/if_pppox.h` 各结构体后缀 `} __packed;` 报 redefinition | 该 uapi 头使用内核内部限定符 `__packed` 但从未定义它 | ohos_compat.h 中 `#define __packed __attribute__((packed))` |
| 4 | `l2tpns.c:1931/1963` `struct msghdr` 位置初始化器把 `NULL` 喂给 int 成员 | OHOS musl 的 msghdr 是 `int msg_iovlen` + 64 位平台 `int __pad1`（与 glibc 的 size_t 布局不同），位置初始化器整体错位 | patch 0003：改用 C99 指定初始化器（`.msg_name/.msg_namelen/.msg_iov/.msg_iovlen`），跨 glibc/musl 可移植 |
| 5 | Makefile 的 `-DHAVE_EPOLL` 由 `uname -r | perl` 探测 | 依赖构建机 perl；无 perl 时管道输出空、条件恒真（碰巧正确但非确定性，且有 shell 噪声） | patch 0001：直接 `DEFINES += -DHAVE_EPOLL`（OHOS 内核恒有 epoll） |
| 6 | 上游 `l2tpns.LIBS = -lcli -ldl`；OHOS 无独立 libdl | musl 把 dlopen/dlsym 放在 libc | 配方以 `l2tpns.LIBS=<绝对路径>/libcli.a` 覆盖：同时去掉 `-ldl` 并把 libcli 以显式静态归档路径传入（implement-policy #5 显式链接闭包：isfile 守卫 + 绝对路径输入，不依赖 `-l` 隐式查找或运行期 rpath） |
| 7 | `make install` 不可用（`install -o root -g root`、gzip、mknod /dev/net/tun） | E108：鸿蒙缺 GNU install，且 install 目标要求 root | 配方绝不执行 install，逐产物 copy 交付 l2tpns/nsctl/8 插件/COPYING |
| 8 | INCLUDES 需要加 libcli 头目录 | libcli.h 来自 conan 依赖包 | 命令行覆盖 Makefile 自身的 `INCLUDES`（而非 CPPFLAGS），保留 `-DLIBDIR/-DETCDIR` 等 DEFINES 不被冲掉 |

## 运行期说明（如实声明，不虚构可运行结论）
- `l2tpns` 守护进程完整运行需要：root 或 CAP_NET_ADMIN、`/dev/net/tun`、
  内核 L2TP（genetlink）或 PPPoE、`/etc/l2tpns/startup-config`。真机实测
  （2026-09-23）：内核 L2TP 缺失已坐实——`/proc/net/protocols` 无 l2tp
  条目、`/proc/net/genetlink` 不存在，L2TP 数据面内核接口不可用；
  `/dev/ppp` 节点存在（root:root 660，非 root 不可 open）；`/dev/net`
  目录存在但不可遍历（`/dev/net/tun` 节点存在性未证实）。综合判断：
  完整数据面在当前 OHOS 上不可运行（L2TP 无内核接口，TUN/PPP 叠加
  权限与节点可达性限制）；包按「编译验证 + 产物级断言」交付，数据面
  运行验证待内核能力与部署权限具备后另行评估。
- 二进制在 OHOS 真机可加载可执行：test_package 以参数解析 usage 路径
  （`l2tpns --version` → 打印 Args are: → exit 0，在任何守护进程初始化之前）
  作为执行门禁，不真启守护进程。
- `garden.so` 插件调用 iptables（运行期依赖系统 iptables，OHOS 缺失时该
  插件功能降级，不影响构建与其他插件加载）。
- 8 个插件经 `dlopen(RTLD_NOW)` 加载，未定义符号仅 libc（已核对
  garden.so 动态符号表）；静态链接 libcli 后 l2tpns 的 DT_NEEDED 仅
  `libc.so`，无 rpath 依赖。

## test_package 覆盖（OHOS 特有，6 项断言）
1. `l2tpns --version` usage 路径 exit 0（OHOS 真机可执行门禁）
2. 二进制内嵌 `L2TPNS version 2.5.0`（上游 ci-test.sh 版本断言的静态降级）
3. 二进制引用 epoll API（`-DHAVE_EPOLL` 补丁分支真实生效）
4. 二进制无 `libdl.so`（`l2tpns.LIBS` 去 `-ldl` 生效）
5. 8 个插件均为 ELF ET_DYN（插件集完整交付）
6. `bin/nsctl` 为 ELF 可执行
（另以 informational 记录 `nsctl --version` 退出码：需活动控制端点，预期非零。）

## 验证结果
- 真机手动 make 全量编译通过（0 error）；产物 l2tpns/nsctl/8 插件齐全。
- `readelf -d l2tpns`：DT_NEEDED 仅 `libc.so`；`strings` 内嵌
  `L2TPNS version 2.5.0`；`l2tpns --version` exit 0；`nsctl --version` exit 1
  （无控制端点，informational）。
- 权威 CI（ci/conan/build_and_test.sh，profile ohos-aarch64）结果见本 run
  CI 日志（Coordinator 汇总回填）。
