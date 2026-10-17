# ircd-irc2 2.11.2p3-dfsg 适配笔记

## 打包环境
- **类型**: 经典 IRC 服务器（irc2 系列，C + autotools），产出 **5 个可执行**：`ircd`、`chkconf`、`iauth`、`ircd-mkpasswd`、`ircdwatch`
- **打包日期**: 2026-10-08
- **平台**: arm64-ohos（OpenHarmony PC）
- **依赖**: `libxcrypt/4.5.2`（提供 libcrypt，`crypt()` 做口令哈希）+ `zlib/1.3.1.1`（`--with-zlib` 压缩链接）
- **状态**: built

## 打包步骤（conan create 全流程）

```bash
conan create archives/i/ircd-irc2/2.11.2p3-dfsg \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码（source()）
Debian 的 dfsg 版 orig tarball：`ircd-irc2_2.11.2p3~dfsg.orig.tar.gz`（sha256 `ed013090…`）。
上游原站 `ftp.irc.org` 不可达；dfsg 版仅移除非自由文档，代码与上游一致。

### 2. 构建方式（照抄 Debian 的权威步骤）
irc2 的构建入口有**两层**：顶层 `configure` 是**自写 shell 脚本**（`config.guess` 后建 `${rev}` 目录），
真正可用的 autoconf 是 **`support/configure`**（带 `--prefix`、`--with-zlib`、`--with-logdir` 等，
并会 `checking for crypt in -lcrypt`）。`debian/rules` 的 `override_dh_auto_configure` 给出的权威做法是：

```sh
mkdir builddir
cp support/configure builddir/
cd builddir && ./configure \
    CFLAGS="$CFLAGS $CPPFLAGS" LDFLAGS="$LDFLAGS" \
    --build=… --host=… --prefix=/usr --sbindir=/usr/sbin --sysconfdir=/etc/ircd \
    --with-logdir=/var/log/ircd --with-rundir=/var/run/ircd \
    --with-zlib --enable-ipv6
make -C builddir all
```

本配方完全照此结构：`generate()` 用 `AutotoolsToolchain`（追加 `--with-zlib --enable-ipv6`）+
`AutotoolsDeps`（把 **libxcrypt/zlib 的 include/lib 注入 CPPFLAGS/LDFLAGS**，让 support/configure 的
`AC_CHECK_LIB(crypt)` / `AC_CHECK_HEADER(zlib.h)` 命中）；`build()` 里建 `builddir`、复制
`support/configure` 进去并在其内 configure，然后 `make all`。

### 3. 打包（package()）
按 Debian 的产物清单（`override_dh_install` 逐个 `cp` 到 `usr/sbin`）把 **5 个二进制装到 `bin/`**：
`ircd`、`chkconf`、`iauth`、`ircd-mkpasswd`、`ircdwatch`（任一缺失即让 build 失败，避免"静默缺产物"）。

## 依赖核查（R35，逐个版本实测）

| 依赖 | 结论 |
|---|---|
| `libxcrypt/4.5.2` | **Install finished successfully** ✓（提供 `libcrypt`，`crypt()`） |
| `libxcrypt/4.4.36` | 仓库有该目录但 **Unable to find** ✗（未发布）——**只有 4.5.2 可用** |
| `zlib/1.3.1.1` | **Install finished successfully** ✓ |

教训：同一库在仓库里可能有多个版本目录，必须按**目录里列出的版本逐个探测**，不能凭目录名判断可用。

## 上游测试清点（R51）

| 项 | 值 |
|----|----|
| 测试文件 | **无**：源码树内无 `t/`、无 `test/`、无 check 类目标（`find src -name "*test*"` 为空；`Makefile.in` 仅存在于 `support/` 且无 check target） |
| 结论 | **上游确无测试** → 上游通过率记 **N/A**（如实披露，不虚构） |
| 消费者验证 | `test_package/check_binaries.py` 4 项（5 个二进制齐备/可执行 → AArch64 ELF 审计 → ircd 指纹（版本串 + crypt 符号）→ best-effort 真跑 `chkconf`） |

## 实测结果（本地 conan create，2026-10-08）

```
ircd-irc2/2.11.2p3-dfsg: Apply patch (portability): …setpgrp…（见补丁 0001）
ircd-ircd2…: Apply patch (portability): …getpass…（见补丁 0002）
ircd-irc2/2.11.2p3-dfsg: [package] 安装 5 个二进制：ircd, chkconf, iauth, ircd-mkpasswd, ircdwatch
[ok]   五个二进制齐备、非空、可执行：ircd, chkconf, iauth, ircd-mkpasswd, ircdwatch
[ok]   五个二进制均为 64 位 AArch64 ELF
[ok]   指纹正确：ircd 含版本串 2.11.2p3、ircd-mkpasswd 含 crypt 符号引用
[ok]   chkconf 真跑成功（exit=0）：initconf(): ircd.conf = /usr/local/etc/ircd.conf
checks=4 fails=0 skips=0
RESULT: PASS
```

- 上游通过率：**N/A**（上游无测试，清点证据见下节）
- 消费者校验：**4 项全部通过**（含真跑 `chkconf`，exit=0）

### 本轮实际解决的 7 个坑（都可复用）

1. **依赖必须按"目录里列出的版本"逐个探**：`archives/l/libxcrypt` 有 4.4.36 与 4.5.2 两个版本目录，
   **只有 4.5.2 能解析**（4.4.36 实测 `Unable to find`）→ 不能凭目录名判断可用。
2. **autotools 工具的导入路径**：`from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps`
   （写成 `conan.tools.autotools` 会 `ModuleNotFoundError`；全仓既有配方均为 `conan.tools.gnu`）。
3. **`builddir` 必须位于源码树内**：irc2 的 `config.status` 用 `Makefile:../support/Makefile.in`、
   `version.c.SH:../ircd/version.c.SH.in` 这类**相对上一级**的模板路径（Debian 也是 `mkdir builddir`
   在源码里再 `cd builddir`）；放到 Conan 构建目录后模板解析不到，Makefile 生成不出来。
   配合声明 `layout()`（`basic_layout`）让 `source_folder` 指向真正的源码树。
4. **`builddir/config.h` 必须先就位**：Makefile 的 `bsd.o: … config.h` 等规则依赖它；
   upstream 由 **`support/config.h.dist`** 提供（Debian 用的是它自己的 `debian/maint/config.h`）。
5. **`config.status` 的临时目录套路在 conan 缓存挂载上会被拒**：
   `rm: ./confstatXXXX/in: Permission denied` / `mv: bad './confstatXXXX/out'` → Makefile 生成失败、
   `make all` 报 `No rule to make target 'all'`。实测换到 `/data/storage/el2/base/cache` 后同一流程正常
   → 配方优先在该可写挂载下构建，不可用时退回构建目录（并在日志给出提示）。
6. **老代码 + 新编译器：C23 的 `f()` 等价 `(void)`** → `s_bsd.c:815` 报
   `too many arguments to function call, expected 0, have 2`。Debian 用 `-std=gnu17` 规避；
   但**irc2 的 Makefile 是 `CFLAGS = $(OPTIMIZE) …`，会覆盖工具链传入的 CFLAGS**（实测
   config.status 记录 `'CFLAGS=-O3'` 却没有该标志）→ 生效位置是 configure 的 `OPTIMIZE=`
   变量（Debian 亦传 `OPTIMIZE=-O2`）。本配方传 `OPTIMIZE='-O2 -std=gnu17'`。
7. **两处 musl 与 glibc 的 API 差异**（各一个 portability 补丁，glibc 路径均保持原样）：
   * `setpgrp`：musl 只声明 `void setpgrp(void)`，irc2 在非 glibc 平台落到 2 参 BSD 形式
     `setpgrp(0, getpid())` → 编译错误（补丁 0001 改用 POSIX `setsid()`）；
   * `getpass`：musl 不提供 → 链接 `ircd-mkpasswd` 报 `undefined symbol: getpass`
     （补丁 0002 在非 glibc 下换成读 `/dev/tty`（回退 stdin）的等价本地实现）。

另：消费者校验自身也踩过一次坑——把 `crypt` 符号断在 `ircd` 上（服务端并不链 libcrypt，
真正使用方是 `ircd-mkpasswd`），以及漏判 `chkconf` 的 `exit=0` 正常路径，两处都已修正。

## 复用来源

- C + autotools 包的范式（`AutotoolsToolchain` + `AutotoolsDeps` + `configure_args` + 产物装 `bin/`）
  沿用同域先例 `archives/n/ngircd/28`（同为 IRC 服务端）；
- "只有具名环境信号才允许 SKIP"的消费者校验口径沿用本会话 PR #14983/#15010 的修正。
