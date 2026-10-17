# E2164 — 鸿蒙 PC 竞赛非特权终端中 VPN/TUN 服务端的运行边界与可验证范围（ocserv 案例）

## 适用条件

- 当前官方鸿蒙 PC 竞赛非特权终端（uid 20020084，非 root，CapEff=0x2a，Seccomp=2）
- 目标库：ocserv（OpenConnect VPN 服务端）1.5.0，Issue #2402，分支 feat/ocserv-1.5.0
- 构建系统：Meson（已弃 autotools/CMake），安装目标 sbindir（ocserv/ocserv-worker）、bindir（occtl/ocpasswd）、libexecdir（ocserv-fw）、/etc/ocserv/ocserv.conf
- 依赖：gnutls/3.8.10、nettle/3.10.2.1、libev/4.33、libedit/20240817、talloc/2.4.4、lz4/1.10.0、libtasn1/4.21.0（均通过 ohpcd 制品仓获取）；protobuf-c 使用上游内置（local-protobuf=true，官方 tarball 自带预生成 .pb-c 文件）；ncurses/6.4 由 libedit 间接依赖自动拉取

## 平台边界证据（真机实测定）

### 1. TUN 设备不可访问

**命令与输出：**
```
open("/dev/net/tun", O_RDWR) → errno=13 (EACCES, Permission denied)
stat /dev/net/tun → Permission denied
ls /dev/net/ → Permission denied
```

**结论：** 沙箱 DAC 或 seccomp 阻止对 /dev/net/tun 的访问，返回 EACCES 而非 ENOENT，说明设备节点存在但被屏蔽。CAP_NET_ADMIN 不在 CapEff 中（0x2a = DAC_OVERRIDE|FOWNER|KILL），无 CAP_NET_RAW、CAP_SYS_ADMIN。

### 2. 网络命名空间创建被拦截

**命令与输出：**
```c
// C 探针：fork() + unshare(CLONE_NEWNET) 在子进程中
CHILD killed by signal=31 (SIGSYS: syscall blocked by seccomp)
```

**结论：** unshare(CLONE_NEWNET) 系统调用被 seccomp filter 以 SIGSYS 拦截。Seccomp=2（SECCOMP_MODE_FILTER），Seccomp_filters=1。对应知识库 E051/E246 先例。

### 3. 网络工具缺失

**命令与输出：**
```
ip, nft, iptables, iptables-nft, unshare → 全 NOT-FOUND（非 PATH 问题，常见 bin 目录均无）
```

**结论：** 系统未安装 iproute2/nftables/iptables/ip-utils 等工具，unshare 无独立二进制（toybox 未实现该 applet）。

### 4. 消费者二进制执行被拒

**命令与输出：**
```
$ /storage/.../bin/ocserv --version
sh: .../ocserv: Operation not permitted (EPERM, rc=126)
```

**结论：** 动态链接 musl 二进制（解释器 /lib/ld-musl-aarch64.so.1，NEEDED libgnutls.so.30、libev.so、libc.so）在沙箱中 exec 被拒。同目录下简单动态二进制（只链接 libc）可执行，说明沙箱在 exec 时检查了二进制加载的共享库路径或 ELF 属性。

## 可验证的非特权范围

### 编译（全通过）

217 个 Meson 构建目标全部编译链接成功，包括：
- src/ocserv（主服务端二进制）
- src/ocserv-worker（工作进程）
- src/ocpasswd（密码管理工具）
- src/occtl（管理工具）
- 所有测试目标（tests/ 下 16+ 个纯单元测试二进制）

### 纯单元测试（15 PASS / 1 SKIP / 0 timeout / 0 failed / 0 errors）

| 测试 | 结果 | 备注 |
|------|------|------|
| str-test, str-test2, json-escape, html-escape, human_addr, ipv4-prefix, ipv6-prefix, port-parsing, proxyproto-v1, proxyproto-v2, cstp-recv, valid-hostname, url-escape, config-inherit, ban-ips | PASS | ban-ips 需 ≥120s 超时（ban_time=30，两次 `sleep(ban_time+1)`，实测约 62s）；config-inherit 经 TMPDIR 补丁(0007)后 `env TMPDIR=<可写目录>` 通过 |
| kkdcp-parsing | SKIP (rc=77) | 上游条件性 skip：`tests/kkdcp-parsing.c:33-34` `#ifndef HAVE_GSSAPI → exit(77)`；gssapi 由 `meson.build:147/343` 的 krb5-gssapi 依赖决定，本归档显式禁用（可选功能，OHOS 无 krb5-gssapi 制品）。保持 skipped，非失败非通过 |

### 阻塞的特权/集成测试

| 测试 | 映射的平台边界 | 证据 |
|------|--------------|------|
| root-tests (root 检查) | 非 root uid 20020084 | /proc/self/status Uid: 20020084 |
| tun-tests (TUN 设备) | open("/dev/net/tun") → EACCES | errno=13 |
| netns 测试 (命名空间) | unshare(CLONE_NEWNET) → SIGSYS | signal 31 |
| firewall 测试 (nftables/iptables) | 工具缺失 | ip/nft/iptables NOT-FOUND |
| 服务监听 (TCP/UDP 443) | 沙箱端口限制 | 按规则不测试 |
| 消费者二进制执行 | exec EPERM | rc=126 Operation not permitted |

## 6 个最小补丁（修复 OHOS 编译/链接问题）

| 补丁 | 文件 | 根因 | 修复方式 |
|------|------|------|----------|
| 0001 | src/common/sockdiag.c | OHOS sysroot 中 linux/socket.h 无条件重定义 sockaddr_storage，与 sys/socket.h 冲突 | 在包含 linux/*.h 前定义 `_UAPI_LINUX_SOCKET_H` 跳过，并 typedef `__kernel_sa_family_t`（netlink.h 需要） |
| 0002 | src/ocpasswd/ocpasswd.c | OHOS musl libc 的 crypt.h 只申明 struct crypt_data 无 crypt() 原型；unistd.h 无 getpass() 原型及实现 | 显式声明 `char *crypt(const char*, const char*)` 和 `char *getpass(const char*)`，并为 getpass 提供真实实现（termios 关闭回显 + /dev/tty 读取） |
| 0003 | src/occtl/meson.build | libedit 依赖 termcap 符号（tputs, tgoto, tgetent 等），但 occtl 链接时未包含 termcap 库 | 在 occtl_deps 后追加 `cc.find_library('termcap')` / 'tinfo' / 'ncurses' 查找 |
| 0004 | src/meson.build | libcommon 静态库的 dependencies 缺 talloc_dep，但 common.h 无条件 include <talloc.h> | 在 libcommon 的 dependencies 中添加 `talloc_dep` |
| 0005 | tests/meson.build | 测试文本包含 src 文件（→ vpn.h → gnutls.h），但 test_base_deps 不含 gnutls_dep | 在 test_base_deps 中添加 `gnutls_dep` |
| 0006 | src/occtl/occtl.c | HAVE_ORIG_READLINE 未定义（用 libedit 而非 readline）时，occtl.c 用 `#define whitespace(x) c_isspace(x)`，但 libedit 不提供 c_isspace | 提供 ASCII whitespace 本地宏定义 `#define c_isspace(x) ((x)==' '||(x)=='\t'||...)` |

## 依赖版本说明

所有依赖版本均使用本轮已验证可获取的版本，保留已证明的版本约束：
- nettle/3.10.2.1（远程只存在 3.10.2.1，3.10.2 未发布 → 不声明 3.10.2）
- libedit/20240817（readline/8.2 远程不存在，readline/8.3 可用但 libedit 更优 → 使用 libedit）
- protobuf-c：远程无发布版本，使用上游内置 protobuf-c（src/protobuf）且官方 tarball 自带预生成 .pb-c 文件，在 notes/manifest 中说明

## 禁止泛化的边界声明

**本观察仅限当前竞赛非特权终端这一运行边界，不得泛化为整个 OpenHarmony 系统不能运行 VPN 服务。** 特权环境（root / CAP 注入 / 白名单放行 / 系统级 seccomp 策略调整）下仍需补测：TUN 建立、netns 集成、nftables 规则注入、真实 VPN 隧道与客户端互联。

## 已复用先例

- E051 / E246：seccomp SIGSYS 拦截导致 syscall 不可用
- E215-draft-C263：OHOS 沙箱无 CAP_NET_ADMIN → setsockopt EPERM
- E091：musl 环境下 sockaddr_storage 冲突修复模式
- DRAFT-pam-wrapper-*：pam_wrapper 运行期经验（ocserv 可选 PAM 功能相关）

## 来源

- 归档：`archives/o/ocserv/1.5.0/`
- 分支：`feat/ocserv-1.5.0`（Issue #2402）
- 官方 tarball（SHA256 42ced08958b9576ab134fcb7bdc7f8df5e13214fd147855f99021fedcf0eedbe）：https://www.infradead.org/ocserv/download/ocserv-1.5.0.tar.xz