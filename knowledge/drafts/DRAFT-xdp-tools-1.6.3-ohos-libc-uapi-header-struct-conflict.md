# DRAFT-xdp-tools-1.6.3-ohos-libc-uapi-header-struct-conflict

**一类问题**：在 OHOS/bionic（musl 系 libc）上，**libc 头**与**内核 UAPI 头**对同一结构体各自定义、且 bionic 未实现 glibc 的
`<linux/libc-compat.h>` 互操作，导致同一 TU 同时包含两套头时冲突。它有两种可复用的形态：

1. **同名双定义**：libc 头无条件定义结构体，内核 UAPI 头也定义（部分带 `__UAPI_DEF_*` 守卫但默认开），例如
   `struct ethhdr`（`netinet/if_ether.h` vs `linux/if_ether.h`）、`struct sysinfo`（`sys/sysinfo.h` vs `linux/sysinfo.h`）。
2. **UAPI 改名**：bionic 把内核 UAPI 的 UDP 头改名为 `struct __kernel_udphdr`，`struct udphdr` 只留在
   libc-only 的 `<netinet/udp.h>`；而 `clang -target bpf` **不能引 libc 头**，内核侧解析助手于是拿到不完备类型。

> 为什么 glibc 不炸而 OHOS 炸：glibc 的 `netinet/if_ether.h` 通过 `libc-compat` 把 `__UAPI_DEF_ETHHDR` 置 0 让内核头退位；
> bionic 的头不做这一步，且直接把结构体写死在 libc 头里。

## 使用说明（判定树 + 修法）

1. **判定别名双定义**：报错形如
   `error: redefinition of 'ethhdr'` / `error: redefinition of 'sysinfo'`，紧跟
   `note: previous definition is here` 指向 `linux/if_ether.h` / `linux/sysinfo.h`。
   取证：
   ```sh
   grep -n '__UAPI_DEF_ETHHDR' "$SYSROOT/usr/include/linux/if_ether.h"   # 有守卫，默认 1
   grep -n 'struct ethhdr'      "$SYSROOT/usr/include/netinet/if_ether.h" # libc 侧无条件定义
   grep -n 'struct sysinfo'     "$SYSROOT/usr/include/sys/sysinfo.h"      # 只有 #ifndef _LINUX_KERNEL_H
   ```
   修法（择一，均为**平台无关自守卫**）：
   - 在会同时看到两套头的 **TU 顶部、任何 include 之前** 置
     `#ifndef __UAPI_DEF_ETHHDR` / `#define __UAPI_DEF_ETHHDR 0`（等价 glibc libc-compat）；
   - 对 sysinfo：`#define _LINUX_SYSINFO_H` 跳过 UAPI 版本，让 libc 定义成为唯一定义。
2. **判定 UAPI 改名**：`clang -target bpf` 编内核侧解析头时报
   `error: arithmetic on a pointer to an incomplete type 'struct udphdr'` +
   `note: forward declaration of 'struct udphdr'`；而 `grep 'struct udphdr' $SYSROOT/usr/include/linux/udp.h` **无命中**，
   只有 `struct __kernel_udphdr`。
   修法：在仅服务 bpf/内核侧的公共头里，用**构建期特性宏**回补 UAPI 定义：
   ```c
   #ifdef HAVE_OHOS_BPF
   struct udphdr { __be16 source; __be16 dest; __be16 len; __sum16 check; };
   #endif
   ```
   特性宏由配方在 configure 后写入生成的 `config.mk`（`HAVE_FEATURES += OHOS_BPF` → `-DHAVE_OHOS_BPF`，同时进
   `CFLAGS`/`BPF_CFLAGS`）。**不要**让 bpf 目标引 `<netinet/udp.h>`（crossover 引 libc 头会引入更多冲突）。

## 适用范围

- OHOS/musl 上一切同时（直接或经第三方头传递）包含 libc 网络头与内核 UAPI 头的 C 项目；
- 尤其：`clang -target bpf` 的 eBPF 程序（不能用 netinet）；被 libpcap/libbpf 等把 UAPI 头拉进 TU 的用户态程序。
- **不适用**：glibc 环境（libc-compat 已处理）；或只包含单一体系头、不触发同名的场景。

## 输入输出定义

| | |
|---|---|
| 输入 | 报错日志；OHOS sysroot 头文件的实际定义（`netinet/*.h`、`sys/*.h`、`linux/*.h`）；bpf 目标编译参数 |
| 输出 | 消除 redefinition 的自守卫（`__UAPI_DEF_ETHHDR=0` / `_LINUX_SYSINFO_H`），或回补的 `struct udphdr` UAPI 定义 |
| 成功判据 | 报错 TU 编译退出码 0；对象文件生成（如 `xdpfilt_dny_udp.o`）；`clang -target bpf` 产物 `llvm-readelf -h` 显示 `Machine: Linux BPF` |

## 示例（xdp-tools 1.6.3，真实四段式）

- **首错①**（`logs/025c-conan-create-cross.log`）：
  `lib/testing/test-tool.c` 经 `xdpsock.h` 引 `<netinet/ether.h>`：
  `.../netinet/if_ether.h:113:8: error: redefinition of 'ethhdr'` /
  `.../linux/if_ether.h:129:8: note: previous definition is here`
  → 补丁 `0001-lib-testing-test-tool.c.patch` 顶部置 `__UAPI_DEF_ETHHDR=0`。
- **首错②**（`logs/025d-conan-create-cross.log`）：
  `xdp-filter` 编 `xdpfilt_dny_udp.o` 时
  `headers/xdp/parsing_helpers.h:283:8: error: arithmetic on a pointer to an incomplete type 'struct udphdr'`
  → 补丁 `0007-headers-xdp-parsing_helpers.h.patch`，以 `#ifdef HAVE_OHOS_BPF` 回补 `struct udphdr`；
  配方在 `config.mk` 注入 `HAVE_FEATURES += OHOS_BPF`。
- **首错③**（`logs/025e-conan-create-cross.log`）：
  `xdp-dump` 编 `xdpdump.c`（pcap 拉入 UAPI sysinfo）：
  `.../sys/sysinfo.h:11:8: error: redefinition of 'sysinfo'` /
  `.../linux/sysinfo.h:23:8: note: previous definition is here`
  → 补丁 `0003-xdp-dump-xdpdump.c.patch`，顶部 `#define _LINUX_SYSINFO_H`。
- **首错④（真机原生 CI，#61090）**：`xdp-filter.c:19 → lib/util/params.h:9 → sysroot/linux/in.h:24 → linux/socket.h:23: error: redefinition of 'sockaddr_storage'`（`sys/socket.h:377 previous`）。
  与 E091/E119 同族，但触发路径是 **sysroot 的 `<linux/in.h>`**（`-I headers` 无法改其解析），WSL 交叉因 include 顺序不同未暴露；
  → 补丁 `0010-lib-util-params.h.patch`：TU 顶部先 `#include <sys/socket.h>`，置 `_UAPI_LINUX_SOCKET_H` + `typedef unsigned short __kernel_sa_family_t`（libbpf `netlink.c` 同源）。
- **修复后**：`xdp-filter`（10 个 BPF 对象）、`xdp-loader`、`xdpdump` 全部构建；W3 本地 CI 模拟通过
  （`archives/x/xdp-tools/1.6.3/reports/w3-local-ci.log`，L0/L1 pass，`.ci-result.json exit_code=0`）。

## 查重差异表（与最相近条目逐条比）

| 维度 | E091（define-guard） | E119（macro-guard-skip-header） | 本条 |
|---|---|---|---|
| 结构体 | 仅 `sockaddr_storage` | 仅 `sockaddr_storage` | `ethhdr`、`sysinfo`、`udphdr`；并补充 **sysroot `<linux/in.h>` 触发的 `sockaddr_storage`** 路径（patch 0010） |
| 机制 | 定义自守卫跳过 `linux/socket.h` | 宏守卫跳过内核头 | ①`__UAPI_DEF_ETHHDR=0`/跳过 UAPI；②**UAPI 改名**后回补结构体 |
| 目标 | 用户态程序 | 用户态程序 | 还覆盖 `clang -target bpf`（**不能用 libc 头**） |
| 关键证据 | OHOS SDK `linux/socket.h` vs `sys/socket.h` | 同 | bionic 把 UDP 头改名 `__kernel_udphdr`；libc 头无条件定义 ethhdr/sysinfo |

词边界查重（`knowledge/{graph,drafts,doc}` 本次实测）：
`__UAPI_DEF_ETHHDR`、`__kernel_udphdr`、`struct udphdr`、`struct ethhdr`、`netinet/if_ether.h`、`struct sysinfo`、`sys/sysinfo.h` **全部 0 命中**；
最相近的 E091/E119 只覆盖 `sockaddr_storage`，故本条的"改名型 + bpf 无 libc"是新差异。

## 验证证据

```
# 1) sysroot 事实（OHOS SDK 15.0.4）
$ grep -n 'struct __kernel_udphdr' $SYSROOT/usr/include/linux/udp.h
22:struct __kernel_udphdr {
$ grep -n 'struct udphdr' $SYSROOT/usr/include/netinet/udp.h
18:struct udphdr {
$ grep -n '__UAPI_DEF_ETHHDR' $SYSROOT/usr/include/linux/if_ether.h
125:#ifndef __UAPI_DEF_ETHHDR
  128:#if __UAPI_DEF_ETHHDR    # libc 侧 netinet/if_ether.h 无此守卫，无条件定义

# 2) 三次首错 → 三个补丁（见上"示例"）
# 3) 修复后整树构建 + W3 通过
$ tar -xzf xdp-tools-1.6.3.tar.gz && patch -p1 < 三个补丁 && make -j1
    CLANG xdpfilt_dny_udp.o ... CLANG xdpfilt_alw_all.o ; CC xdp-filter ; CC xdp-loader ; CC xdpdump
$ python3 scripts/ohc-run.py finish xdp-tools 1.6.3 built        # W3 PASS
  ✅ 本地 CI 模拟通过 (reports/w3-local-ci.log)
```

来源事件：xdp-tools 1.6.3 OHOS 适配（任务 #12086，分支 `feat/xdp-tools-1.6.3`），2026-09-25。
