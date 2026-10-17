# xdp-tools 1.6.3 适配笔记

- 目标库：**xdp-tools 1.6.3**（KIND：目标库；任务 #12086，分支 `feat/xdp-tools-1.6.3`）
- 上游：`github.com/xdp-project/xdp-tools`，tag `v1.6.3` → commit `8fbad9f0af621a22aa87ff2520b3735915b1f0fd`
- 内容：XDP/eBPF 用户态工具集 —— `xdp-loader`、`xdp-filter`、`xdpdump`（`xdp-loader`/`xdp-filter` 是**子命令式 CLI**；`xdpdump` 用共享选项解析器）
- 与同源姊妹配方 `libxdp/1.6.3` 共用同一官方 release 资产；libxdp 只编 `lib/libxdp`，本库编整棵工具树

## 编译环境
- 构建系统: 手写 shell `configure` + GNU Make（非 autoconf）
- 编译日期: 2026-09-25
- 编译器: OHOS SDK clang 15.0.4（`aarch64-unknown-linux-ohos-clang`；BPF 对象用 `clang -target bpf`）
- 交叉 profile: `ohos-aarch64-wsl`（build=x86_64 Linux → host=OHOS/aarch64）
- 状态: built

## 编译步骤
1. 源码：官方 release 资产 `xdp-tools-1.6.3.tar.gz`（sha256 `b4c30d10…`，自含 `lib/libbpf` 子模块）
2. 依赖：`libbpf/1.5.1`（静态；`FORCE_SYSTEM_LIBBPF=1` 走 pkg-config 路径）+ `libpcap/1.10.6`（xdp-dump 的 `USER_LIBS=-lpcap`）
3. 配方 `build()`：`configure` → 向生成的 `config.mk` 追加 `HAVE_FEATURES += OHOS_BPF` → `make V=0 -j1`
4. `package()`：`make install PREFIX=<package_folder>`
5. 关键命令：
   ```
   conan create archives/x/xdp-tools/1.6.3 -pr:h=ohos-aarch64-wsl -pr:b=default -r=ohpcd --build=missing
   ```
   → `Package '…' created` / `EXIT=0`

## 上游测试申报（R51 清点）
- 测试入口：**`make test`** → `lib/testing/test_runner.sh <test-file>` 驱动各工具 `tests/test-*.sh`
- 全树注册用例 **68 个 / 8 个脚本**（`grep '^ALL_TESTS='` 实测）：lib/libxdp 10 + xdp-filter 11 + xdp-loader 8 + xdp-dump 15 + xdp-bench 13 + xdp-forward 6 + xdp-monitor 1 + xdp-trafficgen 4（bpftool 可用时全部可构建）
- `xdp-filter/tests/` 另有 unittest 方法（`test_basic.py` + `test_slow.py`，实际执行 **45** 条，含继承自 `XDPCase` 的方法），不在 `ALL_TESTS` 注册内；合计 **113**
- `test_runner.sh:check_prereq()` 要求：**EUID=0**、`unshare -n -m`、`mount -t bpf /sys/fs/bpf`，以及
  `NEEDED_TOOLS="capinfos ethtool ip ping sed tc tcpdump timeout tshark nft socat ndisc6 arping"`
- **执行口径（2026-09-26 真跑）**：上游测试在 **x86_64 Linux 原生（WSL2 内核 `6.18.33.2-microsoft-standard-WSL2`，真 root）** 执行：
  - `make test`：**62/68** 通过、5 失败、1 跳过
  - `make -C xdp-filter test TESTS='test_python_basic test_python_slow'`：**45/45** 通过
  - **合计 107/113（94.7%）**；5 条失败全部是 WSL 内核特性限制（nft `flowtable` 未编入内核；AF_XDP `-u` 需 `MAP_HUGETLB` 大页而 WSL 上限 6×2MB；另 1 条 `test_capt_pcap` 抓包时序 flaky，复跑可过→最佳 108/113），1 条 `test_xsk_non_privileged` 因 root 运行按设计跳过
  - 复现脚本 `upstream-native/run-all.sh`；结果汇总见 `UPSTREAM-TESTS.md`
- OHOS 无 BPF syscall（seccomp 拦截 SIGSYS，见 `libxdp/1.6.3` 与 `libbpf/1.5.1` 实测），故本配方**不把 `make test` 放进 `build()`**（否则 CI 必红）；设备侧只跑 L1 消费者用例。详见 `test_package/MANIFEST.yml` 的 `upstream_execution`。
- L1 消费者用例（9 断言，均不触碰 BPF syscall）：3 个产物可执行性 + `xdp-loader help`/`xdp-filter help`/`xdpdump --help` 的 usage + `xdpdump --version` 的 1.6.3 横幅 + `xdp-loader load --help`/`xdp-filter load --help`。注意 `xdp-loader`/`xdp-filter` 是子命令 CLI，**没有顶层 `--version`**（只有 `xdpdump` 支持 `--help/--version`）。

## 遇到的问题与解决方案

| # | 问题（首错原文摘要） | 根因 | 解决方案（补丁） |
|---|------|------|----------|
| 1 | `header/linux/compiler-gcc.h … Please don't include <linux/compiler-gcc.h> directly` | OHOS sysroot `linux/stddef.h` → `linux/compiler_types.h` 触发 vendored tools 守卫 | `0004`/`0005`：vendored `compiler.h`/`compiler_types.h` 调整 include 顺序（沿用 libxdp 补丁） |
| 2 | `sockaddr_storage` redefinition：`linux/socket.h` vs `sys/socket.h` | OHOS 头文件冲突（E119 同族） | `0006`：vendored `linux/if_link.h` 平台无关自守卫（沿用 libxdp 补丁） |
| 3 | `lib/util/util.c:179 undeclared 'secure_getenv'` | configure 报 `secure_getenv support: no`（musl/OHOS 无公开 secure_getenv），但 util.c 无守卫 | `0002`：util.c 加 `HAVE_SECURE_GETENV` 回退（`getauxval(AT_SECURE)`），与 libxdp `compat.h` 同构 |
| 4 | `lib/libxdp/compat.h`：`use of undeclared identifier 'libc'` | musl 内部 `libc.secure` 对外不可见 | `0008`（沿用 libxdp 补丁）；`0009` 测试头同步 |
| 5 | `test-tool.c`：`redefinition of 'ethhdr'`（`netinet/if_ether.h` vs `linux/if_ether.h`） | OHOS libc `netinet/if_ether.h` 无条件定义 `struct ethhdr` | `0001`：TU 顶部置 `__UAPI_DEF_ETHHDR=0`（glibc libc-compat 等价） |
| 6 | `parsing_helpers.h`：`arithmetic on a pointer to an incomplete type 'struct udphdr'` | OHOS/bionic UAPI 把 struct 改名为 `struct __kernel_udphdr`，`struct udphdr` 只在 libc-only `netinet/udp.h` | `0007`：`#ifdef HAVE_OHOS_BPF` 补回 UAPI 定义；配方在 config.mk 注入 `HAVE_FEATURES += OHOS_BPF` |
| 7 | `xdpdump.c`：`redefinition of 'sysinfo'`（`sys/sysinfo.h` vs `linux/sysinfo.h`） | pcap 拉入 UAPI `linux/sysinfo.h`，与 libc `sys/sysinfo.h` 冲突 | `0003`：`#define _LINUX_SYSINFO_H` 跳过 UAPI 版本 |
| 8 | 真机原生 `xdp-filter.c:19 → lib/util/params.h:9 → sysroot/linux/in.h:24 → linux/socket.h:23: redefinition of 'sockaddr_storage'`（`sys/socket.h:377 previous`） | `<linux/in.h>` 经 **sysroot** 拉入 `linux/socket.h`，绕过 vendored `if_link.h` 自守卫；WSL 交叉 include 顺序不同未暴露，**仅真机原生 CI 触发** | `0010`：`lib/util/params.h` 顶部先 `#include <sys/socket.h>`，再置 `_UAPI_LINUX_SOCKET_H` + `typedef unsigned short __kernel_sa_family_t`（E119 / libbpf `netlink.c` 同源） |

## 源码修改（patches/，共 10 个，均为 portability）

```
0001-lib-testing-test-tool.c.patch          __UAPI_DEF_ETHHDR=0 消除 ethhdr 双定义
0002-lib-util-util.c.patch                  secure_getenv 的 AT_SECURE 回退
0003-xdp-dump-xdpdump.c.patch               _LINUX_SYSINFO_H 跳过 UAPI sysinfo
0004-headers-linux-compiler.h.patch         vendored compiler.h include 顺序
0005-headers-linux-compiler_types.h.patch   vendored compiler_types.h 守卫
0006-headers-linux-if_link.h.patch          sockaddr_storage 平台无关自守卫
0007-headers-xdp-parsing_helpers.h.patch    OHOS __kernel_udphdr → struct udphdr 回补
0008-lib-libxdp-compat.h.patch              secure_getenv 回退（与 libxdp 同源）
0009-lib-libxdp-tests-test_utils.h.patch    测试头 include compat.h
0010-lib-util-params.h.patch                params.h 的 sysroot linux/socket.h sockaddr_storage 自守卫（真机 CI 修复）
```
补丁由 `refresh-patch --auto` 从 `.orig`/`.work` 差异生成（`.work` 为独立副本，非硬链接）。

## 依赖版本

| 依赖 | 版本 | 来源 | 状态 |
|------|------|------|------|
| libbpf | 1.5.1 | conan ohpcd（静态；传递 elfutils/0.195、zlib/1.3.1.1） | ✅ 已发布 |
| libpcap | 1.10.6 | conan ohpcd（xdp-dump） | ✅ 已发布 |
| m4 | 1.4.19 | conan ohpcd（构建工具，设备自带亦可） | ✅ 已发布 |

## 验证结果

```
export CC=<OHOS cross clang> FORCE_SYSTEM_LIBBPF=1 …（配方 _env 注入）
configure → libbpf support: system v1.5.1（15 项符号探针全 yes）；secure_getenv: no；cap-ng: no
make → xdp-filter / xdp-loader / xdpdump 三个工具 + lib/libxdp.a/.so + BPF 对象全部构建成功
conan create archives/x/xdp-tools/1.6.3 -pr:h=ohos-aarch64-wsl -pr:b=default -r=ohpcd --build=missing
→ Package 'd1238582b2d6a0c18d1f1c54973571a945ea9289' created   EXIT=0
日志：/mnt/e/dsh working/tasks/xdp-tools-1.6.3-2026-09-25/logs/025f-conan-create-cross.log
```

## 交付物

| 文件 | 说明 |
|------|------|
| `sbin/xdp-loader`、`sbin/xdp-filter`、`sbin/xdpdump` | 三个 CLI（ELF aarch64 PIE，动态链 musl + elfutils 系） |
| `lib/bpf/*.o` | 内嵌 BPF 对象（xdp-dispatcher、xdpfilt_*、xdpdump_* 等 13 个） |
| `lib/libxdp.a`、`lib/libxdp.so.1.6.0`、`lib/pkgconfig/libxdp.pc` | 随树内 libxdp 一起安装（上游 `make install` 行为） |
| `include/xdp/*.h` | 公共头（libxdp / parsing_helpers / xdp_helpers 等） |
| `share/xdp-tools/` | 上游测试脚本与测试对象（test_runner.sh 等） |
| `commands.json`（软件级） | R38：本包含可执行文件 |

## 注意事项
1. **bpftool 缺失 → 只出 3 个工具**：上游 `configure` 探测 `bpftool gen skeleton` 失败即清空 `BPFTOOL`，
   顶层 Makefile 随之不构建 `xdp-bench/xdp-forward/xdp-monitor/xdp-trafficgen`。这是上游在缺 bpftool 环境下的
   既定行为（本机、OHOS SDK、conan 仓均无 bpftool），不是适配缺陷。
2. **libpcap 注入**：走系统 libbpf 时 `configure` 会跳过 `check_pcap`，配方显式把 libpcap 的 `-I/-L` 注入 `CFLAGS/LDFLAGS`。
3. **CLI 形态**：`xdp-loader`/`xdp-filter` 是子命令 CLI（`help` / `<cmd> --help`，**无顶层 `--version`**）；`xdpdump` 用 `lib/util/params.c` 的共享选项解析器，支持 `--help/--version`（后者打印后返回 `EXIT_FAILURE`，上游行为），test_package 只断言输出内容。
4. **R40 适配完整性（需人工确认）**：xdp-tools 的核心能力是经 **BPF syscall 加载/挂载 XDP 程序**，OHOS 无 BPF syscall（seccomp SIGSYS），因此本次仅验证 `conan create` 交叉编译 + 打包 + 3 个 CLI 的 help/version 冒烟（W3 实跑 9/9）；**XDP load/attach 运行路径无法验证**，适配完整性需人工确认，不能理解为可在鸿蒙上运行 XDP。
5. **知识归属（路径 B 差异表）**：同源 libxdp 1.6.3 已有 4 条草稿（`clang -target bpf` sysroot 头缺失 / vendored kernel-tools 编译器守卫 / seccomp `unshare` SIGSYS / 上游测试不可运行）。
   本库新增的**构建编排类**差异：多工具 + 缺 bpftool 的选择性构建、libpcap 仅在系统-libbpf 分支外注入、OHOS UAPI 结构改名（`__kernel_udphdr`）与 libc/UAPI 头双定义（ethhdr/sysinfo）——这些在 libxdp 只编 `lib/libxdp` 时**不会触发**。
---

**编译结束**: 2026-09-25 19:56
**最终状态**: built
