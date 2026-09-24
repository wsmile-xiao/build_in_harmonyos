# ypserv 4.2 适配笔记

## 编译环境
- 构建系统：autotools（tarball 自带预生成 `configure`，不需要 autoreconf/automake）
- 上游：https://github.com/thkukuk/ypserv ，tag `v4.2`（2021-09-06 发布）
- 源码：`ypserv-4.2.tar.xz`（178292 B）
  sha256 `68357588814fff5169d7c0e7eb0a2754088ecf0a498ccac6c8b44d9acafe9f77`
- 目标平台：OpenHarmony PC / OHOS 6.0 / aarch64（armv8）/ musl / clang 15 / libc++
- 语言：纯 C（`lang-preflight` → `detected=c`）
- 编译日期：2026-09-22
- 状态：built（conan create + conan-verify 通过；`make check` 2/2 通过）

## 编译步骤（真实命令）

```bash
# 依赖（全部 ohpcd 已发布，全部取静态变体）
conan install --requires=libnsl/2.0.1 --requires=gdbm/1.23 \
              --requires=libxcrypt/4.5.2 -r=ohpcd \
              -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
              -g PkgConfigDeps --output-folder=<deps>

# 配置（PKG_CHECK_MODULES 需要 .pc；gdbm/libxcrypt 需要 -I/-L）
sh ./configure --prefix=/ \
    CPPFLAGS="-I<gdbm>/include -I<libxcrypt>/include -I<libnsl>/include -I<libtirpc>/include/tirpc" \
    LDFLAGS="-L<gdbm>/lib -L<libxcrypt>/lib -L<libnsl>/lib -L<libtirpc>/lib -Wl,--allow-multiple-definition" \
    PKG_CONFIG_PATH=<deps>

make -j1
make check            # lib/test-securenets + lib/test-ypserv_conf
make install DESTDIR=<pkg>     # 配方内由 package() 执行
```

配方（`conanfile.py`）把上面的标记位固化：`PkgConfigDeps` 提供 `.pc`，
`extra_cflags`/`extra_ldflags` 注入 gdbm/libxcrypt 的 `-I`/`-L` 与
`-Wl,--allow-multiple-definition`，`build()` 里 `PKG_CONFIG_PATH` 指向 `generators_folder`。

## 遇到的问题与解决方案（按出现顺序）

| # | 问题（真实报错） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `checking for gdbm_open in -lgdbm... no` → `You need the GNU GDBM, QDBM, Tokyo Cabinet or the Solaris NDBM functions for this package !` | `configure.ac` 用**裸** `AC_CHECK_LIB(gdbm, gdbm_open)`，只有 `-lgdbm`，没有依赖的 `-L/-I`；conan 的 `AutotoolsToolchain` 不会自动注入依赖路径 | 配方 `generate()` 显式注入 `-I<gdbm>/include`、`-L<gdbm>/lib`（libxcrypt 同理）；libnsl/libtirpc 走 pkg-config |
| 2 | `./config.status[794]: can't create ./confaAilJc/subs1.awk: Permission denied` / `config.status: error: could not setup config files machinery` | autoconf 的 `config.status` 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录；HMDFS 上 0700 目录对下一个进程不可进入（同 libnsl/2.0.1） | 补丁 0001：`configure` 内 `umask 077` → `umask 022`（共 2 处） |
| 3 | `lib/access.c:296:15: error: a function declaration without a prototype is deprecated in all versions of C [-Werror,-Wstrict-prototypes]` | `announce_ready()` 定义没写 `void`，但 `lib/access.h:40` 自己声明为 `(void)`；`lib/Makefile.am:21` 带 `-Werror` | 补丁 0002：定义改为 `announce_ready(void)` |
| 4 | `ypserv/ypserv.c:383:30: error: use of undeclared identifier 'O_RDWR'`（并伴随 `call to undeclared function 'open'`） | 只 include 了 `<sys/file.h>`；glibc 间接带入 `<fcntl.h>`，musl 不会 | 补丁 0008：补 `#include <fcntl.h>` |
| 5 | `ld.lld: error: duplicate symbol: xdr_ypresp_all` / `xdr_ypresp_maplist`（`ypserv_xdr.c` ↔ `libnsl.a:yp_xdr.o`） | `ypserv/ypserv_xdr.c` 自带**回调式**的这两个 XDR 编解码器，静态 `libnsl.a` 的 `yp_xdr.o` 也定义同名符号。Linux 上 libnsl 是共享库，可执行文件的定义直接抢占、不报错；静态库则硬报重复 | 配方注入 `-Wl,--allow-multiple-definition`（实测只有这 2 个符号冲突，且必须让 ypserv 自己的定义生效） |
| 6 | `ypxfr.c:501:14: error: incompatible integer to pointer conversion assigning to 'char *' from 'int'` | `ypxfr.c` 缺 `<string.h>`（隐式声明 `strerror/strcmp/memset/strcpy/strncpy/strchr`），且使用了 GNU 专有的 `strdupa()`（alloca 版栈拷贝），musl 不提供 | 补丁 0009：补 `<string.h>`；`#ifndef strdupa` 时给出与 glibc 等价的宏定义 |
| 7 | `update.c:176/471/564: assigning to 'struct spwd */struct passwd *' from 'int'`（并伴随 `sgetspent/putspent/lckpwdf/ulckpwdf/getspnam/fgetpwent/putpwent` 隐式声明告警） | musl 的 `<shadow.h>` 只声明 `struct spwd`，**一个函数都没有**；glibc / shadow-suite 的整套口令库流式接口缺失 | 补丁 0005 新增 `ohos-musl-compat.h`：按 `/etc/passwd`、`/etc/shadow`、`/etc/group` 格式**真实解析/写出**，`fcntl()` 锁 `/etc/.pwd.lock`；补丁 0006/0007 在两个 TU 里 include |
| 8 | `yphelper.c:384:15: assigning to 'struct group *' from 'int'`（`fgetgrent` 未声明） | 同上，`fgetgrent` 也缺 | 纳入补丁 0005（`yp_fgetgrent`，含成员列表拆分） |
| 9 | `make check`：`FAIL test-ypserv_conf` + `Signal 11 (core dumped)` | `lib/ypserv_conf.c:551` 在“Malformed network/netmask entry”分支里 `free(tmp->map)`，而 `tmp->map` 此时**尚未赋值**（先 malloc 了 `tmp`，`map` 在后面才 strdup）。glibc 下 malloc 常返回零内存，`free(NULL)` 无害；musl 复用已释放块，直接 SIGSEGV | 补丁 0004：删掉该 `free(tmp->map)`，只 `free(tmp)` |
| 10 | `make check`：`FAIL test-securenets` + `getnetconfigent (udp) failed` | `test-securenets.c` 用 `getnetconfigent()` 查传输，libtirpc 把 `/etc/netconfig` **硬编码**（1.3.7 不支持 `NETCONFIG` 环境变量）；OHOS 镜像无该文件，`/etc`（→`/system/etc`）只读，无法补齐 | 补丁 0003：先按原逻辑查库；仅当查不到时用内存中的 `struct netconfig`（netid + `NC_TPI_CLTS` + protofmly）代替，上游 5 条断言不变 |
| 11 | （本地探索期）`make clean` 后 `No rule to make target 'yppush.8'` | 上游 `yppush/Makefile.am:13 CLEANFILES = *~ ${MANS}` 会把分发的 `yppush.8` 删掉 | 不要在本地对该包执行 `make clean`（配方不含 clean） |

## 源码修改（补丁清单）

见 `conandata.yml` 的 9 个补丁与 `manifest.yaml` 的 `patch_classification`。摘要：

- `0001-configure.patch` — HMDFS：`umask 077` → `022`
- `0002-lib-access.c.patch` — `announce_ready(void)` 原型一致
- `0003-lib-test-securenets.c.patch` — 无 netconfig 数据库时的等价回退（上游测试用例修改，断言不变）
- `0004-lib-ypserv_conf.c.patch` — 修复 free 未初始化指针（上游潜伏 bug）
- `0005-ohos-musl-compat.h.patch` — **新增** `ohos-musl-compat.h`（musl 口令库兼容层，真实实现）
- `0006-rpc.yppasswdd-update.c.patch` / `0007-yphelper-yphelper.c.patch` — 引用兼容头
- `0008-ypserv-ypserv.c.patch` — 补 `<fcntl.h>`
- `0009-ypxfr-ypxfr.c.patch` — 补 `<string.h>` + `strdupa` 兼容定义

全部补丁已用「原始 tarball 副本 + `patch -p1` 逐个应用」验证：与工作树逐字节一致。

## 依赖版本
| 依赖 | 版本 | 类型 | 说明 |
|---|---|---|---|
| libnsl | 2.0.1 | 强制（静态） | `yp_*` 客户端接口、`rpcsvc/ypclnt.h`、`rpcsvc/yp_prot.h` |
| libtirpc | 1.3.7 | 强制（静态） | TI-RPC/XDR、`rpc/rpc.h`；同时是 libnsl 的硬依赖 |
| gdbm | 1.23 | 强制（静态） | DBM 后端；选 1.23 是因为它的二进制是静态的（1.24 为 shared，会产生 `libgdbm.so.6` 运行期依赖） |
| libxcrypt | 4.5.2 | 强制（静态） | `crypt()`，供 `rpc.yppasswdd` |

9 个可执行文件 `readelf -d` 仅 `NEEDED libc.so`。

## 验证结果

```bash
# 上游测试（build() 内执行）
$ make -j1 check
Testsuite summary for ypserv 4.2
# TOTAL: 2   # PASS: 2   # FAIL: 0   # SKIP: 0   # ERROR: 0
#   PASS test-securenets (exit status: 0)
#   PASS test-ypserv_conf (exit status: 0)

# 消费者视角（test_package/test.sh，12 项断言）
✅ ypserv/rpc.ypxfrd/rpc.yppasswdd/yppush/makedbm/mknetid/revnetgroup/yphelper --version -> 4.2
✅ ypxfr --version 静默（上游行为），-h usage OK
✅ yphelper --merge_passwd：fgetpwent/fgetspent 兼容层解析 passwd+shadow（OHOS 特有）
✅ yphelper --merge_group ：fgetgrent 兼容层解析 group+gshadow（OHOS 特有）
✅ makedbm：gdbm（静态）映射存取往返
```

`rpc.yppasswdd/rpc.yppasswdd:146` 这类需要真实 `/etc/shadow` 的路径未做端到端改写验证
（会在系统口令库上产生副作用），其口令库读写由兼容层的语义测试覆盖。

### CI 门禁分项说明（W3 本地 CI 实测）

- `G0 / KC / JC / L0 / L1 / L5 = pass`，`Pass rate 100% (1/1)`，`JC6 涉及软件数: 1（合规）`。
- `L2 = skip`：CI 的 smoke 检查只找 `bin/` 目录，本包按上游布局装在 `sbin/` 与 `lib/yp/`，故跳过（非失败）。
- `L4 = warn`：CI 规则 `(strcpy|sprintf|gets|strcat)\b` 命中 `patches/0005`。其中 3/4 命中来自
  `fgets (` —— 该正则的 `gets\b` 会匹配 `fgets`，属规则误报；余下 1 处 `strcpy` 已改为
  `memcpy (buffer, line, strlen (line) + 1)`（前置已有 `strlen (line) >= sizeof (buffer)` 边界保护）。
  因此该 warn 无法通过改代码消除，不影响 L0/JC 通过。

## 运行期前置条件（阻塞项，重要）

`libtirpc` 硬编码 `/etc/netconfig`。`ypserv` 启动即 `__rpc_setconf("netpath")`，缺失时
日志 `could not read /etc/netconfig, exiting..` 并退出（`ypserv/ypserv.c:448-453`）。
OHOS 系统 `/etc` 只读且无该文件，**平台镜像必须提供 `/etc/netconfig`**
（内容同 `libtirpc` 包内 `etc/netconfig`）。该限制影响所有基于 libtirpc 的程序
（如 autofs），不是 ypserv 独有；已在上层报告与本笔记中如实记录。

## 复现 / 排查入口
- 构建日志：`reports/` 内各阶段日志（依赖准备、configure、make、make check、install）
- 上游测试逐项日志：`reports/upstream-test-*.log`
- 测试报告：`reports/test-report.md`
---

**编译结束**: 2026-09-22 02:20
**最终状态**: built
