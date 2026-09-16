# blockdomains

blockdomains 是基于黑名单的域名过滤守护进程，通过 `libnetfilter_queue` 挂接
iptables NFQUEUE，识别 HTTP `Host:` 头与 TLS SNI，对命中黑名单（含子域）的
连接下发 DROP 裁决，并内置裁决缓存。

## 功能概述

- iptables NFQUEUE 用户态包过滤（IPv4/IPv6 TCP）
- HTTP `Host:` 与 TLS Client Hello SNI 域名识别
- 后缀匹配黑名单（`.acl` 文件，`/etc/blockdomains/acl/` + `blocked/` 启用链接）
- 裁决决策缓存（1024 槽哈希表）
- `blockdomainsctl`（POSIX sh）手动控制脚本与 SysV/systemd 服务脚本

## OHOS 适配

### 适配要点

- **绕过上游 Makefile**：上游 Makefile 内嵌 `dpkg-buildflags`（Debian 专用），
  OHOS 上不可用；recipe 在 `build()` 中直接用工具链 clang 编译
  `src/blockdomains.c`、`src/cache.c`、`src/database.c` 并链接
  `-lnetfilter_queue`
- **sockaddr_storage 重定义**：HarmonyOS（musl + Linux uapi 头文件）下
  `<linux/netfilter.h> → <linux/in.h> → <linux/socket.h>` 会与
  `<netinet/in.h>` 已引入的 `<sys/socket.h>` 冲突；补丁在首个 Linux uapi
  网络头前定义 `_UAPI_LINUX_SOCKET_H` 并补充
  `__kernel_sa_family_t` typedef（同 babeld 1.13.1 先例）
- **musl 缺 __compar_fn_t**：`database.c` 的 `qsort` 比较器 casts 依赖
  glibc 内部 typedef `__compar_fn_t`；补丁在非 glibc 下条件提供该 typedef
- **man 页未构建**：上游 man 页需 asciidoctor，属运行非必需文档，未纳入包

## 依赖关系

### 编译依赖

- `libnetfilter_queue`（上游 `-lnetfilter_queue`）—— 已入档
  （`archives/l/libnetfilter_queue`）并发布到制品仓，CI 依赖发布检查
  （L0i R36）通过，CI 构建图正常解析
- `libnetfilter_queue` 自身依赖 libmnl、libnfnetlink（作为传递依赖拉入，
  两者均已入档）

### 运行依赖

- `libc.so`（musl）
- 运行时功能依赖内核 NFQUEUE 支持与 `iptables`（NFQUEUE target），
  无内核 NFQUEUE 时程序在 `nfq_open()` 处以退出码 1 报错（属预期行为）

## 参考资料

- 上游仓库：https://git.rrq.au/rrq/blockdomains.git
- Debian 源码页：https://deb.debian.org/debian/pool/main/b/blockdomains/

## 版本列表

| 版本 | 状态 | 编译日期 | Conan 引用 |
|------|------|----------|------------|
| [0.1](./0.1/) | built（权威 CI 全 PASS） | 2026-09-13 | blockdomains/0.1 |
