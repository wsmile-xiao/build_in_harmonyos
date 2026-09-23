# libnfsidmap-ldap

## 简介

NFSv4 ID 映射库（libnfsidmap）及其 LDAP 映射插件 `umich_ldap`。

上游已把 libnfsidmap 并入 nfs-utils 源码树（`support/nfsidmap/`），因此本包版本号
2.6.4 即 nfs-utils 的版本号，源码取 nfs-utils 官方 tarball；`-ldap` 后缀指明
LDAP 映射插件（`umich_ldap.so`）这一包身份。

## 产物

- `lib/libnfsidmap.so.1.0.0`（+ `.so`/`.so.1` 符号链接、静态库 `libnfsidmap.a`）
- `lib/libnfsidmap/{nsswitch,static,regex,umich_ldap}.so`（由 libnfsidmap 运行时 dlopen 的映射插件）
- `include/nfsidmap.h`、`include/nfsidmap_plugin.h`
- `lib/pkgconfig/libnfsidmap.pc`
- `share/man/man3/nfs4_uid_to_name.3`、`share/man/man5/idmapd.conf.5`

## OHOS 适配

- 构建系统: autotools（in-tree 构建；上游 `support/*` Makefile 不支持 VPATH）
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- `config.guess`/`config.sub` 增加 HarmonyOS/ohos 三元组（E007/E122），不使用 `--build/--host`
- `configure`：getrpcbynumber 树级硬门禁降级为警告；config.status 临时目录改为 `$$` 名 + `umask 000`（HMDFS，E110/E112/E118）
- `support/nfs/conffile.c`：weak `versionsort()`/`strverscmp()`（musl 缺失，E534）
- 插件记录 `DT_NEEDED libnfsidmap.so.1`：HarmonyOS 下 dlopen 的对象只从自有 DT_NEEDED 闭包解析符号，否则任何插件都无法加载

## 依赖

- openldap/2.6.7（LDAP 插件本体）
- krb5/1.22.1（GSS / LDAP SASL 分支）
- cyrus-sasl/2.1.28（`sasl_interact_t` → ENABLE_LDAP_SASL）
- libevent/2.1.13、uuid/2.40.1、libtirpc/1.3.7、sqlite3/3.49.1（nfs-utils 顶层 configure 无条件门禁）

## 参考

- 官网: https://linux-nfs.org/
- 源码: https://cdn.kernel.org/pub/linux/utils/nfs-utils/2.6.4/nfs-utils-2.6.4.tar.xz
