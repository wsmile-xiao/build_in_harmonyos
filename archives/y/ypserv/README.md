# ypserv

## 简介
`ypserv` 是 NIS（YP，Network Information Service）v2 服务器套件，由 Thorsten Kukuk 维护。
它把 `/etc/passwd`、`/etc/group`、`hosts`、`netgroup` 等系统文件按域编译成 DBM 映射，
并通过 Sun RPC 对外提供查询；同时提供主从服务器之间的映射分发（`rpc.ypxfrd`、
`ypxfr`、`yppush`）与口令修改（`rpc.yppasswdd`）。

注意：这是 NIS v2 服务器，**不是** NIS+（NIS v3）。

## 打包内容

| 路径 | 内容 |
|---|---|
| `sbin/ypserv` | NIS 服务端守护进程 |
| `sbin/rpc.ypxfrd` | 映射文件传输服务（主→从） |
| `sbin/rpc.yppasswdd` | 口令修改服务 |
| `sbin/yppush` | 主动推送映射到从服务器 |
| `lib/yp/makedbm` | 文本 → DBM 映射编译工具 |
| `lib/yp/mknetid` | 生成 `netid.byname` 映射 |
| `lib/yp/revnetgroup` | 生成 `netgroup.byuser/byhost` 映射 |
| `lib/yp/yphelper` | 辅助工具：合并 passwd/shadow、group/gshadow，输出主机名/主服务器 |
| `lib/yp/ypxfr` | 从服务器按需拉取映射 |
| `lib/yp/ypxfr_1perhour` 等脚本 | `ypMakefile` 使用的定时拉取脚本 |
| `include/rpcsvc/ypxfrd.x` | `rpc.ypxfrd` 的 RPC 协议定义 |
| `etc/ypserv.conf`（未安装，见下） | 上游示例配置，tarball `etc/` 内 |

## OHOS 适配
- **musl 口令库缺口**：musl 的 `<shadow.h>` 只有 `struct spwd`，没有任何函数；
  glibc / shadow-suite 的 `fgetpwent`/`putpwent`/`fgetgrent`/`sgetspent`/`fgetspent`/
  `putspent`/`getspnam`/`lckpwdf`/`ulckpwdf` 全部缺失。`patches/0005-ohos-musl-compat.h.patch`
  新增 `ohos-musl-compat.h`，按 `/etc/passwd`、`/etc/shadow`、`/etc/group` 的冒号分隔格式
  **真实解析/写出**，并用 `fcntl()` 对 `/etc/.pwd.lock` 加锁（不是空壳 stub）。
  `rpc.yppasswdd/update.c` 与 `yphelper/yphelper.c` 引用该头文件。
- **依赖发现**：`configure.ac` 用 `PKG_CHECK_MODULES`（libnsl/libtirpc）与裸
  `AC_CHECK_LIB`（gdbm/libcrypt）探测依赖，因此配方同时提供
  `PKG_CONFIG_PATH`（PkgConfigDeps 生成的 `.pc`）和 `-I/-L`（gdbm、libxcrypt）。
- **重复符号**：`ypserv/ypserv_xdr.c` 自带回调式 `xdr_ypresp_all()`/`xdr_ypresp_maplist()`，
  静态 `libnsl.a` 的 `yp_xdr.o` 也定义同名符号。Linux 上靠共享库符号抢占静默解决，
  静态库下必须显式 `-Wl,--allow-multiple-definition`，且可执行文件自身的定义优先。
- **HMDFS**：autoconf `config.status` 的临时目录用 `umask 077` 创建，在 hmfs/hmdfs 上
  下一个进程无法进入（`Permission denied: config.status: error could not setup config files machinery`），
  放宽为 `022`。
- **clang 15 严格性**：`announce_ready()` 定义与自身头文件声明不一致（`-Werror` + `-Wstrict-prototypes`）；
  `ypserv.c` 缺 `<fcntl.h>`；`ypxfr.c` 缺 `<string.h>` 且使用 GNU 专有 `strdupa()`。
- **上游潜伏 bug**：`lib/ypserv_conf.c` 在“网络/掩码非法”分支里 `free()` 了一个尚未赋值的
  `tmp->map`，glibc 下 malloc 返回零内存侥幸不崩，musl 下直接 SIGSEGV。

## 依赖
- `libnsl/2.0.1`（`yp_*` 客户端接口，静态；其 `requires` 硬依赖 `libtirpc/1.3.7`）
- `libtirpc/1.3.7`（TI-RPC + XDR，静态）
- `gdbm/1.23`（DBM 后端，静态；选 1.23 而非 1.24 是因为 1.23 的二进制是静态的）
- `libxcrypt/4.5.2`（`crypt()`，静态）

9 个可执行文件仅 `NEEDED libc.so`，运行期不解析任何第三方 `.so`。

## 运行期前置条件（重要）
`libtirpc` 把 netconfig 数据库路径 **硬编码**为 `/etc/netconfig`（1.3.7 不支持任何环境变量
覆盖）。`ypserv` 启动时会 `__rpc_setconf("netpath")`，读不到就打印
`could not read /etc/netconfig, exiting..` 并退出；`access.c`/`server.c` 的每次请求判定也要用它。
OHOS 系统镜像不提供该文件且 `/etc`（→ `/system/etc`）只读，因此**部署 ypserv 前必须由平台镜像
提供 `/etc/netconfig`**（内容可取 `libtirpc` 包内的 `etc/netconfig`：`udp/tcp/udp6/tcp6/rawip/local/unix`）。
`make check` 的 `test-securenets` 同样需要该数据库，补丁 0003 让它在数据库不可用时用等价的
内存中 `struct netconfig` 代替，从而在 OHOS 上仍能验证 `securenet_host()` 的匹配逻辑。

## 功能验证
```bash
# 工具可用性
ypserv --version && makedbm --version && yphelper --version

# 鸿蒙特有：musl 口令库兼容层（passwd+shadow / group+gshadow 合并）
yphelper --merge_passwd /etc/passwd /etc/shadow
yphelper --merge_group  /etc/group  /etc/gshadow

# DBM 映射往返
printf 'alpha\tvalue-one\n' > /tmp/in.map && makedbm /tmp/in.map /tmp/out.map && makedbm -u /tmp/out.map
```

## 参考
- 上游仓库：https://github.com/thkukuk/ypserv
- `ypserv(8)`、`ypserv.conf(5)`、`makedbm(8)`、`yphelper(8)`（包内 `share/man`）
