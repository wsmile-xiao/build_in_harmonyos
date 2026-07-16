# lldpd 1.0.21 适配笔记

## 软件概述

lldpd 是 IEEE 802.1AB (LLDP) 的实现，同时兼容 CDP/EDP/SONMP/FDP。本包构建产物：

| 产物 | 类型 | 安装位置 | 说明 |
|------|------|----------|------|
| `lldpd` | 守护进程 | sbin/ | 监听网络接口收发 LLDP 帧；运行需 root 与原始套接字 |
| `lldpcli` | 命令行客户端 | sbin/ | 通过 Unix 域套接字与 lldpd 通信，查询邻居信息 |
| `liblldpctl` | 静态库 | lib/ | 客户端 C 库，提供机箱/端口 atom 编解码与连接管理 API |
| `lldpctl.h` / `lldpctl.hpp` | 头文件 | include/ | liblldpctl 公共接口 |
| `lldpctl.pc` | pkg-config | lib/pkgconfig/ | 依赖描述 |

## 构建系统与配置选项

构建系统为 autotools (configure + make + libtool 2.4.6)。关键配置选项：

- `--with-embedded-libevent`：lldpd 源码树内置 libevent 副本 (`libevent/` 目录)。使用内
  置副本可零外部依赖编译，**无需引入 conan libevent 包**。注意：libevent 仅被守护进程
  和客户端二进制链接，liblldpctl 本身不依赖 libevent (`src/lib/` 不含任何 event2/ 头)。
- `--disable-privsep`：特权分离默认开启，需要专用 lldpd 用户/组与 chroot 目录，OHOS 无此
  设施，故关闭。
- `--disable-hardening`：hardening 默认开启，会探测 `-fstack-protector*` / `-D_FORTIFY_SOURCE`
  等选项；这些对配方构建无意义且会增加工具链探测复杂度，故关闭。
- `--without-readline` / `--without-snmp` / `--without-seccomp` / `--without-libbsd`：关闭依
  赖 OHOS 不提供的可选库。
- `--disable-doxygen-doc`：不构建文档。

库默认同时构建 shared 与 static（lldpd 源码自带现代 libtool 2.4.6，正确处理 shared 所需
的 PIC）。liblldpctl 带版本脚本 (`lldpctl.map`) 与 `-version-info 14:0:10`。

## OHOS 平台适配（内联补丁，build() 中完成）

源码自带 `config.guess` / `config.sub` 时间戳为 2022-01-09，**不识别 HarmonyOS/ohos**。本
机构建容器 `uname` 报告 Linux，故此处不触发；但 CI 真实 worker `uname` 报告 HarmonyOS，
若不补丁 configure 将无法识别平台 (E007)。因此在 `build()` 内联补丁：

- `config.guess`：增加 `__OHOS__` 的 LIBC 探测分支；增加 `*:HarmonyOS:*:*)` 情况，映射到
  `aarch64-unknown-linux-ohos` 三元组。
- `config.sub`：在 kernel 列表增加 `linux-ohos`，在 OS 列表增加 `ohos*`。
- `configure`：将 `umask 077` 改为 `umask 022`，避免 HMDFS 下 config.status 创建的临时目录
  owner 无写权限 (E011)。

以上均为生成文件的运行时修补，与 libident/addrwatch/bird 等已合入配方一致，不放入
`patches/`。

## OHOS/musl 头文件缺口（自包含 compat 头，build 时生成）

lldpd 源码自带部分 `include/linux/` UAPI 头，但依赖系统的内核头与 BSD 队列头。OHOS/musl
工具链（含本机构建容器）既无内核 UAPI 头，也无 `sys/queue.h`（musl 刻意不提供）。编译报：

- `include/linux/types.h` → `<asm/types.h>`、`<linux/posix_types.h>` 缺失
- `include/linux/netlink.h` → `<linux/socket.h>` 缺失（仅需 `__kernel_sa_family_t`）
- `include/linux/sockios.h` → `<asm/sockios.h>` 缺失
- `src/marshal.c` 等大量源文件 → `<sys/queue.h>` 缺失（TAILQ_* 宏）

`generate()` 中在源码目录生成自包含 `ohos-compat/` 头树并加入 `-I`，补齐这 5 个头：

| 头文件 | 内容 |
|--------|------|
| `asm/types.h` | `__u8..__u64` / `__s8..__s64`（aarch64 LP64 内核整型） |
| `asm/sockios.h` | `SIOCGSTAMP` / `SIOCGSTAMPNS` 等常量 |
| `linux/posix_types.h` | `__kernel_long_t` / `__kernel_fd_set` / `__kernel_fsid_t` 等 |
| `linux/socket.h` | 仅 `__kernel_sa_family_t`（按 netlink.h 注释所需） |
| `sys/queue.h` | 复用源码树内置 libevent 的 `libevent/compat/sys/queue.h` |

此法在容器（无内核头）与 CI worker（有内核头，compat 头内容等价）行为一致，配方无需依赖
系统是否已装内核头，确定性更好。lldpd 自带的 `src/compat/` 已覆盖 asprintf/strlcpy/
strndup/strnlen/strtonum/getline 等 musl 函数缺口，无需额外处理。

## liblldpctl 静态构建（规避 HMDFS 运行时加载问题 E079/E050）

configure 增加 `--disable-shared --enable-static`，仅产出 `liblldpctl.a`。

**背景**：曾尝试构建共享库 `liblldpctl.so`，但 CI worker 文件系统为 HMDFS，即便已把
soname/dev 符号链接物化为真实 ELF 文件（已验证包内确含 `liblldpctl.so.4` 真实文件），
test 运行时仍报 `Error loading shared library liblldpctl.so.4` —— 怀疑 conan 缓存路径
本身在 HMDFS 上对动态加载器不可达。容器（ext4）下则一切正常，故为 HMDFS 特有。

**修法**：改静态构建。`liblldpctl.a` 已并入 `libcommon-daemon-lib` + `libfixedpoint`
便利库对象，且 liblldpctl 本身不依赖 libevent（仅守护进程/客户端二进制依赖），故静态
消费者只需 libc 即可链接。test 与 lldpcli 静态链入 liblldpctl 后无 `DT_NEEDED
liblldpctl.so.4`，彻底消除运行时 .so 查找。

容器验证：包内仅 `liblldpctl.a`/`.la`（无 `.so`）；独立编译的消费者 `DT_NEEDED` 仅
`libc.so`，运行输出默认传输路径；test_package 8 断言通过。

## 无外部 conan 依赖

`--with-embedded-libevent` 内置编译 libevent，故 `requirements()` 为空，不触发 R36 依赖
发布检查。

## test_package 设计 (R34)

lldpd 上游 `tests/` 目录提供基于 libcheck 的单元测试 (`check_lldp.c`、`check_cdp.c` 等)，
以及一个 `decode.c` 离线解码工具。但这些测试依赖内部 `src/daemon/lldpd.h` 结构体与 PCAP
样本，属于守护进程内部 API，不适合作为 Conan **消费者**测试，且 `make check` 额外需要
libcheck。因此 `upstream_test_in_build: false`。

`test_package/test.c` 验证 liblldpctl 的**公共 C API**（消费者视角），且**离线运行**（无需
运行中的 lldpd）：

1. `lldpctl_get_default_transport()` 返回默认 Unix 控制套接字路径（`LLDPD_CTL_SOCKET` 常量），
   断言非空。
2. `lldpctl_strerror(LLDPCTL_ERR_CANNOT_CONNECT)` 返回人类可读错误串，断言非空。
3. `lldpctl_new(NULL, NULL, NULL)` 分配连接句柄。关键：`lldpctl_new` → `lldpctl_new_name`
   仅分配结构并建立内部自管道 (`pipe()`)，**不立即连接** Unix 套接字——连接在 `sync_send`/
   `sync_recv` 实际发送请求时才建立 (`conn->fd == -1` 时惰性 `connect`)。故无运行中 lldpd
   亦可测试。
4. `lldpctl_last_error(conn)` 断言新连接无错误 (`LLDPCTL_NO_ERROR`)。
5. `lldpctl_release(conn)` 断言返回 0。

共 8 个断言。链接方式：CMakeDeps 生成 `lldpd::lldpd` 目标，test 链接 liblldpctl。

## 容器编译验证结果（本机 hmbs-builder）

- `conan create` 通过；test_package `test_lldpd` 1/1 Passed（8 断言全过）。
- 产物：`lib/liblldpctl.a`（静态）、`lib/pkgconfig/lldpctl.pc`、
  `include/{lldpctl.h,lldpctl.hpp,lldp-const.h}`、`bin/lldpd`、`bin/lldpcli`。
- ELF：`lldpd` / `lldpcli` 均为 ELF 64-bit LSB arm64。
- 动态依赖：静态链入 liblldpctl 的消费者 DT_NEEDED 仅 `libc.so`（无 liblldpctl 运行时
  依赖）；内置 libevent 静态链入，无额外 .so 依赖。

