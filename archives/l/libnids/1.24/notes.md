# libnids 1.24 — 编译进度

> 档案创建时间: 2026-09-18
> 最后更新: 2026-09-18（当前状态）
> 分支: feat/libnids-1.24

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libnids |
| 版本 | 1.24（上游无 1.24.0，官方版本号即 1.24） |
| 状态 | ✅ success（见七、八节） |
| 构建系统 | autotools（autoconf 2.59，手写 Makefile.in，非 automake） |
| 源码 URL | https://downloads.sourceforge.net/project/libnids/libnids/1.24/libnids-1.24.tar.gz |
| sha256 | 314b4793e0902fbf1fdb7fb659af37a3c1306ed1aad5d1c84de6c931b351d359（2026-09-16 对官方发布包核验） |
| License | GPL-2.0-or-later（源码树 COPYING 为 GPLv2 1991-06 全文，src/*.c 头注明 "See the file COPYING for license details"） |
| 真实依赖 | libpcap（硬依赖，编译+链接）；glib/libnet 为可选功能，见下节裁剪 |

## 二、依赖核实与裁剪决策
- **libpcap（必需）**：nids.h API 与全部核心源文件依赖 pcap.h；链接 libpcap。使用本仓库 conan 包 libpcap/1.10.6（ohos-aarch64，静态链入）。
  - configure 的 `--with-libpcap=<dir>` 要求指向 libpcap **源码树**布局（查找 `<dir>/libpcap.a`），不能指向 conan 包目录；改用显式注入 `CFLAGS=-I<pcap include>`、`LDFLAGS=-L<pcap lib>`、`LIBS=-lpcap`。
  - configure 探测成功后只把 `-lpcap` 写入 PCAPLIB，**不**把 include 路径写入 src/Makefile 的 PCAP_CFLAGS → 必须从 CFLAGS 传入 -I，否则 make 报 `pcap.h: No such file or directory`。
- **glib（裁剪）**：`--disable-libglib`。glib 代码路径直接调用 `g_thread_init()`（HAVE_LIBGTHREAD_2_0），该符号自 glib 2.32 起废弃、2.84（ohpcd 可得版本）已移除，永远无法链接；libnids 核心功能不依赖 glib。**glib 不计入依赖**。
- **libnet（裁剪）**：`--disable-libnet`。libnet 仅用于 nids_killtcp()（伪造 RST 杀连接）功能，核心 API（IP 重组/TCP 流重组/回调）不需要；OHOS 无 libnet 包。
- **--host 实测可用（修正先前记录）**：autoconf 2.59 通用模板含 host_alias 处理（configure L438），`--host=aarch64-linux-ohos` 被接受并输出 `checking host system type... aarch64-unknown-linux-ohos`。先前"不认识 --host"的结论是当时 PATH 无 clang 导致 configure 提前失败所致误判。直接以 CC/CFLAGS/LDFLAGS 注入交叉编译器（clang 15，Target aarch64-unknown-linux-ohos，内置 OHOS sysroot）。注意：空 `--sysroot=` 参数会破坏 clang 链接（"C compiler cannot create executables" 假根因），不传即可。

## 三、平台问题与知识库复用（路径 A）
1. **config.guess/config.sub 不识别 aarch64-unknown-linux-ohos** → 0001/0002 最小补丁（cpu list + company list + guess exit 三处），同 libpcap 1.10.6 先例（E007/E160）。
2. **config.status `mktemp -d` 失败（E112 bypass-mktemp 复用）**：OHOS toybox 0.8.12 mktemp -d 生成 mode 2700（drwx--S---）目录，属主 uid 20001006/file_manager，当前用户（uid 20020101）无写权限；hmfs/tmpfs 不按 umask，chmod 静默失败 → autoconf 2.59 config.status 报 `mv: bad './confstatXXX/out': Permission denied`。首次适配用 exit-1 的 mktemp shim 触发 configure L426 plain-mkdir 回退；最终方案改为 **0005 补丁（configure 两处 `umask 077`→`022`，confstat 目录 mode 0755 可写）**，与 E011（HMDFS umask）同族根因。**路径 A 复用，未新建 draft**。
3. **`undefined symbol: rindex`（samples/overflows.c:128）**：上游明文调用 BSD 遗留函数 `rindex(path, '/')`（clang -E 预处理后仍存在，非宏污染；musl 系 OHOS libc 不导出 rindex）。语义等价替换 `strrchr(path, '/')`（POSIX 标准，<string.h> 已包含，参数/返回/NULL 语义 1:1）→ 0004 补丁，基于官方 tarball（sha256 校验后）生成，clean apply 验证通过。**与知识库 DRAFT-cconv-0.6.3-rindex-strrchr 同根因 → 路径 A 复用，未新建 draft**。
4. **src/Makefile.in 共享链接规则丢失 $(LDFLAGS)**（上游 bug）→ 0003 补丁补回，否则 -L<libpcap libdir> 不生效，共享链接找不到 -lpcap。

## 四、构建验证（源码树实测）
| 步骤 | 结果 |
|------|------|
| patch 0001–0004 对干净官方 tarball 应用 | 全部 clean apply（rc=0） |
| configure（shim + 注入 CC/CFLAGS/LDFLAGS/LIBS，--disable-libglib --disable-libnet） | rc=0，生成 src/Makefile、samples/Makefile、src/config.h，`checking for libpcap... yes` |
| make static（src/libnids.a） | rc=0 |
| make shared（src/libnids.so.1.24，-Wl,-soname,libnids.so.1.24） | rc=0 |
| samples 手动 make（顶层 Makefile 的 samples 递归被上游注释，line 11） | rc=0：overflows、printall、sniff 全部编译链接成功（0004 后） |

## 五、上游测试分类（如实核实）
- **上游正式自动测试：0。** 上游无 make check/test 目标（顶层 Makefile.in 目标仅 all/install/static/shared/_install/_installshared/clean/distclean），无 tests/ 目录，无 test harness。
- **samples/ = 上游示例程序，不计入正式测试数**；作为集成验证单独记录：
  - 可构建：overflows、printall、sniff（samples/Makefile all 目标全集）——离线构建通过。
  - 运行时：三者均调用 `nids_init()+nids_run()` 在默认设备（本机 dummy0）上 live capture → `SIOCETHTOOL(ETHTOOL_GLINK) ioctl failed: Permission denied`，rc=1。**需 root/CAP_NET_RAW + 真实网卡 → 环境依赖，不适用（不算 PASS）**。
  - chksum_ctl.c（无 main 的 API 用法片段）、nids_next.c（替换 printall.c main 的片段）非独立程序，不单独构建。
- **test_package 用离线构造 pcap 数据做真实消费者验证**（见六），不以 live capture 为 PASS 前提。

## 六、Conan test_package（真实消费者验证）
- CMake + CMakeDeps 链接安装后的 libnids（shared 与 static 均验证）。
- 离线输入：确定性 pcap 由生成脚本在 test() 开始时产出到构建临时目录（不入库、不回写源码目录；裸二进制 .pcap 无法随 GitCode PR diff 传输，见 packetq 1.7.3 / aircrack 1.7 先例均以 .b64 或脚本方式入库）：
  - `gen_one_tcp_flow.py` → `one_tcp_flow.pcap`（8 包）：完整单流 SYN→SYN/ACK→ACK→双向 PSH 数据→FIN/ACK×2→ACK。IP/TCP 校验和按 RFC1071 预计算（libnids 校验和失败静默丢包）。
  - `gen_flows.py` → `flows.pcap`（12 包）：双并发流 + 1 个故意坏 TCP 校验和段 + 有效重传 + 单流关闭、另一流保持打开。
  - 生成脚本输出字节级可复现（对旧手工 fixture cmp 比对一致后才移除裸 .pcap）。
- fixture 语义预验证（conan create 前）：本地原生编译消费者（clang + libnids.a + libpcap.a）驱动两个 fixture，断言全部命中（JUST_EST/DATA 双向/CLOSE、坏校验和 0 交付、GOOD-DATA 精确重组、est=2/close=1），100% 确定性。
- test_package 断言：
  - single：JUST_EST=1、client data 逐字节 =`GET / HTTP/1.0\r\n\r\n`、server data =`HELLO-LIBNIDS`、CLOSE=1、无 RESET/TIMED_OUT。
  - multi：JUST_EST=2、坏校验和段 0 交付、重传重组 =`GOOD-DATA`、server data 含 `SVC-OK`、CLOSE=1（另一流 EOF 时未关闭）、无 RESET/TIMED_OUT。
  - nids_run() 恒返 0（pcap_loop EOF 也返 0），判定全部来自回调断言（tcp.c L683 实测取证）。
- 无 root、无真实网卡、无公网；不以 live capture 为 PASS 前提。
- test() 显式 self.run()（消费者二进制 ×2 用例 + readelf ELF 检查 ×5）；OHOS 上 /system/bin/sh 不能直接 exec ELF，用 CONFIG_SHELL（bash）包装（实测：sh 直接 exec 本 aarch64 ELF 成功，但按知识库惯例保留 bash 包装以兼容旧固件）。
- HarmonyOS 专项检查：ELF64/AArch64/Type=DYN(PIE)；shared 变体 NEEDED libnids、static 变体无 NEEDED libnids；RPATH/RUNPATH 必须为空（出现即 FAIL）。

## 七、ohos-aarch64 conan create
| 配置 | 结果 |
|------|------|
| shared=True | ✅ RC=0（create + test_package 双用例 PASS + ELF 检查 5/5） |
| shared=False | ✅ RC=0（create + test_package 双用例 PASS + ELF 检查 5/5） |

## 八、补丁清单
| 文件 | 原因 | 方式 | 类型 |
|------|------|------|------|
| 0001-config.guess.patch | 不识别 ohos | cpu/company/exit 三处最小修改 | portability |
| 0002-config.sub.patch | 不接受 aarch64-unknown-linux-ohos | 同 libpcap 先例最小修改 | portability |
| 0003-Makefile.in-shared-link-LDFLAGS.patch | 共享链接规则丢 $(LDFLAGS)（上游 bug） | 补回 $(LDFLAGS) | bugfix |
| 0004-samples-overflows-rindex-strrchr.patch | rindex 在 OHOS libc 无符号 | strrchr 1:1 等价替换 | portability |
| 0005-configure-umask-hmdfs.patch | confstat 临时目录 0700 在 HMDFS 下不可写（E011 同族） | configure 两处 umask 077→022 | bugfix |

## 九、知识库决策记录
- mktemp/HMDFS 根因：E112/E060 已覆盖 → **路径 A**。
- rindex 根因：DRAFT-cconv-0.6.3-rindex-strrchr 已覆盖 → **路径 A**。
- 本次未产生新平台根因，未新建 draft。

## 十、链接产物事实（供终检引用）
- libnids.so.1.24：ELF 64-bit LSB arm64、SONAME=libnids.so.1.24、NEEDED 仅 libc.so（libpcap 静态链入）；包内补 libnids.so→libnids.so.1.24 符号链接（上游 Makefile 只产 SONAME 文件，无 .so 链接）。
- static 包：libnids.a + nids.h；cpp_info.requires 传递 libpcap::libpcap（libnids.a 引用 pcap_* 符号，消费者必须链 libpcap）。
- samples 二进制：`ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`。
- 链接告警（非致命、环境固有）：`-Wl,--code-sign: 'linker' input unused`、`-fuse-ld=lld unused during compilation`。
- 本地开发工具链注意：toybox patch 0.8.12 对无上下文行的 hunk 解析失败（`@@ -N +N @@` 单行替换也会 Hunk FAILED，带 ≥1 行 context 即正常）——生成补丁时必须带 context 行（本次 0005 由 Python 从原文件字节级生成并 dry-run 验证）。

## 结束

本版本适配、构建及测试验证已完成。
