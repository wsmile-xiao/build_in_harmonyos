# thc 3.8 — OHOS 适配笔记

## 软件概况
- 上游：`vanhauser-thc/thc-ipv6` v3.8（THC IPv6 Attack Toolkit）。
- 手写 Makefile 构建，产物为 68 个 PROGRAMS + 5 个 EXTRA 工具（dnssecwalk / dnsdict6 /
  thcping6 / fragrouter6 / connsplit6）+ `thc-ipv6-lib.o` 对象文件。
- 许可证：AGPL-3.0-or-later（强 copyleft，注意分发合规）。

## 依赖（R35/R36 已用 conan download 验证可消费）
- libpcap/1.10.6 — HAVE_SSL 默认开启，LDFLAGS 含 -lpcap。
- openssl/3.5.6 — -D_HAVE_SSL 由 HAVE_SSL=yes 注入，链接 -lssl -lcrypto。
- libnetfilter_queue/1.0.5 — fragrouter6/connsplit6 链接 -lnetfilter_queue（容忍失败）。

## OHOS 适配要点
1. **编译器 (R33)**：CC 取自 conan conf `tools.build:compiler_executables`，默认
   `/data/service/hnp/bin/clang`，禁止裸 shell 变量。
2. **-march=native / -flto**：OHOS clang 不支持（目标 CPU 未知 / 需全程序 LTO 链接），
   由 patch 0001 改为 `-O2 -fPIC -Wall`。
3. **-lresolv / -lrt**：musl 已将 resolver 与实时扩展并入 libc，glibc 下额外的链接标志
   在 musl 下多余，patch 0001 从 dnsdict6 / thcping6 规则中移除。
4. **MANPAGES=**：上游 `all` 目标含 `$(MANPAGES)`，`%.8` 规则会执行每个编译出的二进制来
   生成 man 页；交叉/OHOS 构建下运行主机二进制不安全且会失败，构建时传 `MANPAGES=` 关闭。
   源码树中预置的 `thc-ipv6.8` 仍照常打包到 `share/man/man8`。
5. **依赖路径注入**：musl 不默认搜索依赖 include/lib 目录，构建时通过 CPPFLAGS/LDFLAGS
   显式注入 libpcap/openssl/libnetfilter_queue 的 includedirs/libdirs。

## R8 排查结论（sockaddr_storage 冲突）
首次构建即在 `thc-ipv6-lib.c` 命中与 ipv6toolkit 相同的 `sockaddr_storage` 重定义冲突：
- 触发链：`thc-ipv6-lib.c:30` `#include <sys/socket.h>`（musl 定义 sockaddr_storage，守卫
  `_SYS_SOCKET_H`）→ `:66-73` 在 `SIOCGIFHWADDR` 分支下 `#include <linux/netlink.h>`
  → 传递包含 `linux/socket.h`（守卫 `_UAPI_LINUX_SOCKET_H`）重定义 sockaddr_storage。
- 报错：`linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'`。
- 修复（补丁 0002，特性检测，无 __OHOS__ 宏）：
  ```c
  #ifdef _SYS_SOCKET_H
  #define _UAPI_LINUX_SOCKET_H
  typedef unsigned short __kernel_sa_family_t;
  #endif
  #include <linux/netlink.h>
  #ifdef _SYS_SOCKET_H
  #undef _UAPI_LINUX_SOCKET_H
  #endif
  ```
  预定义 `_UAPI_LINUX_SOCKET_H` 跳过冲突定义，并补 `__kernel_sa_family_t`（asm/types.h 在
  OHOS 未提供）；netlink 之后的 include（thc-ipv6.h 仅含 pcap/endian）不再触发，故 undef 安全。
- 仅 `thc-ipv6-lib.c` 一处包含 linux/netlink.h，68 个工具 .c 均不包含，故单点修复即可。
- R8 合规：全程未引入 `__OHOS__` 平台宏。

## R51 上游测试核验
- 上游仓库 106 文件，仅 `6to4test.sh`（运维脚本），Makefile 无 test/check 目标，
  无 CUnit/CMocka 单元测试。
- 结论：**无上游自动化测试入口**。可行性由 test_package 的消费者冒烟测试承担
  （address6 离线解析 3 个地址，assertion_count=3）。

## 构建链接修复（LDFLAGS 命令覆盖陷阱）
二次构建在 `parasite6` 链接阶段报 `ld.lld: error: undefined symbol: pcap_open_live`
（`thc-ipv6-lib.o` 引用 pcap/ssl 符号全部未解析）。
- 根因：`build()` 以 `make ... LDFLAGS="-L<dirs>"` 形式传依赖库搜索目录；但 GNU make 中
  **命令行变量覆盖 Makefile 内的 `+=` 追加**，上游 Makefile 的 `LDFLAGS += -lpcap -lssl -lcrypto`
  被丢弃，链接行只剩 `-L<dirs>`、无 `-lpcap`，故符号未解析。
- 修复：在 LDFLAGS 中**显式追加依赖库名** `-l<lib>`（libpcap/openssl/libnetfilter_queue 的
  `cpp_info.libs`），不再依赖 Makefile 的 `+=` 追加。
- 副作用：Makefile 自身的 `+=` 若仍生效会产生重复 `-lpcap`（无害）。链接顺序 `$^ ... $(LDFLAGS)`
  保证 `-l` 在对象文件之后，lld 解析正常。

## 消费者测试 (test_package)
- `test.sh` 调用 `address6 <addr>`，离线、无需特权/网络，真实运行二进制并断言非空解析输出。
- OHOS mksh 不能直接 exec ELF，故 test.sh 以 `/data/service/hnp/bin/bash` 为 shebang，
  test_package/conanfile.py 经 `VirtualRunEnv` + `bash test.sh` 运行。
---

**编译结束**: 2026-09-22 01:47
**最终状态**: built
