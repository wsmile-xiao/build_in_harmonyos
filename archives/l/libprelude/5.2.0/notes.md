# libprelude 5.2.0 适配笔记

## 编译环境
- 构建系统: autotools（归档内**没有** autoreconf 产物，需自行 bootstrap）
- 编译日期: 2026-09-17
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，profile `ohos-aarch64`）
- 上游源: https://github.com/Prelude-SIEM/libprelude/archive/refs/tags/5.2.0.tar.gz
  sha256 `8afcfc92735362834111f63520d8d96fed6f76450da1690678fa0afbfef9d742`（1,487,916 B）
- 状态: built（conan create + 上游测试 + test_package 全绿）

> **上游地址说明（PR 正文同步）**：libprelude 原官网域名（prelude-labs.org /
> www.prelude-siem.org）已被劫持失效，官方发布页的 5.2.0 `.tar.gz` 全部 404，
> 无法校验也无法作为可信源；本次改用 Prelude-SIEM **官方 GitHub 组织的 tag 归档**
> 作为上游源（R39 官方托管），并锁定其 sha256。

## 编译步骤

配方 `build()` 的实际流程（等价上游 `autogen.sh`，但绕开制品缺陷，见下表）：

```sh
# 1) 打补丁：configure.ac 切 LTDL_INIT([subproject]) + 去掉 AC_CONFIG_FILES 里的 libltdl/Makefile
# 2) libtool 自举
"$LIBTOOLIZE" -c --force --automake            # tool_requires libtool/2.5.4
# 3) 物化独立 libltdl（libtoolize --ltdl 在本制品里不可用，见问题 #1）
cp -a <libtool 包>/share/libtool  libltdl       # 含 pregenerated configure
# 防御性清理 libltdl/Makefile.in 里未被替换的 @MAINTAINER_MODE_TRUE@ 字面量
# （当前 libtool/2.5.4 制品该文件实测 0 处，保留该步是兼容历史形态的兜底）
# 4) autotools 生成（autoconf/autoreconf 用宿主 HNP 2.72，见问题 #2）
aclocal -I m4 -I libmissing/m4 && autoconf && autoheader
automake --add-missing --copy --foreign
mkdir build-aux && 复制 config.guess/config.sub/compile/... 进去   # libltdl 用 ../build-aux
# 5) OHOS 平台修补
config.guess 注入 HarmonyOS case（E007）
configure 里 umask 077 → 022（E011）
# 6) 构建 + 上游测试
../configure --prefix=/ --disable-maintainer-mode --disable-gtk-doc --disable-easy-bindings \
             --without-swig --without-perl --without-python2 --without-python3 \
             --without-ruby --without-lua --without-valgrind
make -j1
(cd tests && make check)          # 上游 9 个测试
```

## 上游测试清点（R51 申报表）

| 层级 | 来源 | 注册方式 | 数量 |
|------|------|----------|------|
| libprelude 自身测试 | `tests/Makefile.am` 的 `TESTS` | autotools parallel-tests（`make check`） | 9 |
| 随树发布的 gnulib 自检 | `libmissing/tests/`（vendored gnulib） | 同上（顶层 `make check` 会先跑） | 160 |
| 文档/绑定 | `docs/`、`bindings/` | 无测试目标 | 0 |
| 合计 | | | **169** |

`tests/Makefile.am` 的 9 项：`async-timer`、`idmef`、`idmef-criteria`、
`idmef-message-helper`、`idmef-path`、`idmef-value`、`prelude-client`、
`prelude-string`、`prelude-timer`。

实测结果（OHOS aarch64 真机，`conan create` 内执行）：

| 集合 | TOTAL | PASS | SKIP | FAIL |
|------|-------|------|------|------|
| libprelude tests/ | 9 | 9 | 0 | 0 |
| libmissing（gnulib vendored） | 160 | 139 | 18 | 3 |

libmissing 的 3 项失败均为 **vendored gnulib 对 libc/内核行为的自检**，与 libprelude
API 无关，属 HongMeng 内核 / musl 语义差异，未修改、未纳入门禁（配方只在 `tests/`
子目录跑 `make check`）：

| 失败项 | 具体技术原因（实测输出） |
|--------|--------------------------|
| `test-poll` | `Pipe test... failed (expecting POLLHUP after shutdown)` — 管道一端 `shutdown()` 后 HongMeng 内核不在 poll 事件里回报 POLLHUP |
| `test-select-out.sh` | 同一 poll/select 语义差异的 select 侧探针（`test_select` 报 writable 判定与预期不符） |
| `test-sigaction` | `test-sigaction.c:81: assertion 'sa.sa_handler == SIG_DFL' failed` — musl/OHOS 对某些信号 `sigaction` 查询回报 `SIG_IGN`，非 libprelude 代码路径 |
| 18 项 SKIP | 实测原因：`not a native Windows system` ×10、`no french Unicode locale is supported` ×3、`no traditional french locale is supported` ×2、`no transitional chinese locale is supported` ×1、`no traditional japanese locale is supported` ×1、`no locale for testing is supported` ×1，均为缺失 locale / 非 Windows 平台 |

## 遇到的问题与解决方案

| # | 问题（首个真实报错） | 根因 | 最小修改 |
|---|----------------------|------|----------|
| 1 | `libtoolize: error: '…/libtool/share/libtool-conan/libltdl/ltdl.c' not found` ×20 → `autoreconf: error: libtoolize failed with exit status: 1` | 归档没有 configure（必须 bootstrap），而 ohpcd 的 `libtool/2.5.4` 制品把**独立 libltdl 发行版**装到了 `share/libtool/`，`libtoolize --ltdl` 期望的 `share/libtool-conan/libltdl/` 里只剩头文件 | 配方内先 `libtoolize --automake`，再从 tool_requires 的 libtool 包把 `share/libtool/`（含 pregenerated `configure`）物化成 `libltdl/`；顺带对 `libltdl/Makefile.in` 里未被替换的 `@MAINTAINER_MODE_TRUE@` 字面量做防御性清理（其 standalone configure 没有 `AM_MAINTAINER_MODE`，留着会让 make 把占位符当成待生成目标；当前制品实测该文件 0 处，属兼容历史形态的兜底） |
| 2 | `Can't load '…/perl/…/auto/Cwd/Cwd.so' … Permission denied`（`autoreconf`/`automake` 全部起不来） | `autoconf/2.72` 制品的 `.autoreconf-real` shebang 与 `PERL5LIB` 指向包内自带的 `perl/5.42.2`，而 `automake/1.18` 制品的 `.automake-real` shebang 写死了宿主 `/data/service/hnp/bin/perl`；一旦 autoconf 进图，宿主 perl 会去加载 5.42.2 的 XS → ABI 不匹配 | 不 tool_require `autoconf`（宿主 HNP 已是 autoconf/autoreconf 2.72，CI 能力矩阵内 ✅），只补 `automake/1.18` + `libtool/2.5.4`，perl 环境保持自洽 |
| 3 | `libtool: error: '//lib/libgpg-error.la' is not a valid libtool archive`（链接 libprelude.la 时） | E236：依赖链制品的 `.la` 带着打包时的 `prefix=/` 假象（`libdir='//lib'`、`dependency_libs` 引用 `//lib/*.la`），libtool 在同一目录里优先读 `.la` 并追依赖 | 按 E236：把 host 依赖的 `.a/.so*` 复制进 build 私有目录 `.dependency-archives`（跳过 `.la`），并把 generators 目录里每个 `.pc` 的 `-L"${libdir}"` 改写成该目录；Conan 缓存保持只读；package() 里再删掉包内 `*.la` |
| 4 | `configure: error: cannot guess build type; you must specify one` | E007：automake 1.18 自带的 config.guess（2024-07-27）没有 HarmonyOS 分支，`uname -s` = HarmonyOS | 按 E007 给生成的 `config.guess` 注入 `*:HarmonyOS:*:*)` → `GUESS=$UNAME_MACHINE-unknown-linux-ohos`（**不**用 `--build/--host` 伪造三元组）；同版本 config.sub 已识别 `linux-*`，无需再补 |
| 5 | `config.status: error: could not setup config files machinery`（`./confXXXX/subs1.awk: Permission denied`） | E011：HMDFS 的 UID 映射使 `umask 077` 建出的 0700 临时目录对当前进程也不开放写权限 | 按 E011：把 `configure` 里的 `umask 077` 全部放宽为 `umask 022`（2 处） |
| 6 | `ld.lld: error: undefined reference due to --no-allow-shlib-undefined: lt__argz_create_sep`（链 prelude-admin 时；`llvm-nm libltdlc.a` 可见 5 个 `U lt__argz_*`） | 顶层 `AC_CONFIG_FILES([libltdl/Makefile])` 让**父** configure 替换 libltdl 的 Makefile，而父 configure 从没跑过 libltdl 的 `_LT_LIBOBJ` 检查 → `LTLIBOBJS=''`，`libltdlc.a` 少了 `lt__argz.lo`，`libprelude.so` 带着未定义符号出厂 | 源码补丁 `0001-configure.ac.patch`：`LTDL_INIT([recursive])` → `LTDL_INIT([subproject])`，并从 `AC_CONFIG_FILES` 去掉 `libltdl/Makefile`；libltdl 跑自己的 configure 后 `LTLIBOBJS=' ${LIBOBJDIR}lt__argz$U.lo'`，`libltdl/config.h` 也随之生成 |
| 7 | `common.c:41:10: fatal error: 'prelude-error.h' file not found` | 上游 `src/Makefile.am` 用 `-I$(srcdir)/libprelude-error` 引用**生成**头，VPATH（out-of-tree）下该头只在 build 树里 | 布局改为 in-tree（`folders.source == folders.build`），不改上游 Makefile.am |
| 8 | tests/ 里 6/9 项 `FAIL (exit status: 139)`（SIGSEGV） | Conan Release 注入 `-DNDEBUG`，而上游测试把被测 API 写在 assert 参数里（`tests/idmef.c:18 assert(idmef_message_new(&idmef) == 0)`）→ 调用被整体编译掉，后续解引用空对象 | `tc.ndebug = None`：保持优化等级、只不再定义 NDEBUG；**上游测试文件零改动** |
| 9 | 顶层 `make check` 从父目录（`make -C tests check`）跑时 9/9 全 `FAIL (exit status: 127)`，日志 `shell-init: error retrieving current directory: getcwd: cannot access parent directories` | HMDFS 下 libtool wrapper 由 `getcwd()` 反推 `$progdir`，从父目录递归进入时解析成 `<top>/.libs/<test>` → 找不到程序 | 在 `build()/tests` 目录内直接 `make check`（wrapper 解析正确，9/9 通过）；不改上游测试 |
| 10 | test_package 运行期 `Error loading shared library libgnutls.so.30: (needed by libprelude.so.28)` | `gnutls/3.8.10` 制品以 option `shared=False` 发布、包内却只有 `.so`（其 package() 无条件复制 `.libs/*.so*`）→ `require.run` 为 False，Conan 不给下游生成 LD_LIBRARY_PATH | 在 `package_info()` 里按“依赖 lib 目录中确有 `.so`”补 `runenv_info` 的 `LD_LIBRARY_PATH`（对 gnutls/libgcrypt/libgpg-error/libtasn1 生效）；根因是 gnutls 制品自身缺陷，已另行沉淀知识草稿 |
| 11 | 测试消费者程序 `FAIL prelude_string_cat` | `prelude_string_cat()` 返回追加字节数而非 0（上游 `tests/prelude-string.c` 亦按 `>= 0` 断言） | test_package 断言改为 `>= 0`，并继续校验长度与内容 |
| 12 | **CI 构建 #49675（worker CI-020）红**：`# TOTAL: 9 / PASS: 8 / FAIL: 1` → `FAIL: prelude-timer`，随后 `Error in build() method, line 323 … make check` （CI 机器人按关键词把它归类成「Autotools configure 失败」，实际 configure/编译均已通过，日志已进到 `make check`） | 上游 `tests/prelude-timer.c:34` 断言 `elapsed == prelude_timer_get_expire(&timer->timer)` 要求 wall-clock 秒差**精确相等**，高负载 worker 上 ±1s 即失败（本机 8 轮命中 1 次 + CI 命中 1 次，同一项） | `make check || (echo 'retry'; make check)` 的**一次有界重跑**（env 用 `export` 前缀，保证两次都能加载 .so）。9 个用例、181 处断言、上游源码零改动（R51 不减不跳），第二次仍失败则构建照红 |

## CONFIG_SHELL 方案的核验结论（为何未采用）

有人建议「构建阶段传 `CONFIG_SHELL=/bin/zsh` 修复 configure 探测失败」，实测三点不成立，
故本配方保留 bash 路径、不改 shell 相关设置、不新增补丁：

1. `conan.tools.gnu.Autotools.configure` 的签名是 `configure(build_script_folder=None, args=None)`，
   **没有 `env` 形参**，`autotools.configure(env={"CONFIG_SHELL": ...})` 会直接 `TypeError`；
2. 容器/真机上 `/bin/zsh` **不存在**（`ls /bin/zsh → No such file`，zsh 只在 `/usr/bin/zsh`），
   而 profile `ohos-aarch64` 的 buildenv 已导出 `CONFIG_SHELL=/data/service/hnp/bin/bash`；
3. 该轮 CI 的 configure 阶段本就成功（失败发生在 `make check`），改 shell 无对症效果。

## 源码修改

仅 1 个补丁（`patches/0001-configure.ac.patch`，由 `refresh-patch --auto` 生成）：

- `configure.ac`：`LTDL_INIT([recursive])` → `LTDL_INIT([subproject])`（+1/-2）
- `configure.ac`：`AC_CONFIG_FILES([…])` 去掉 `libltdl/Makefile` 一行

补丁不含任何平台宏（`__OHOS__`），对 Linux 同样成立（libltdl 独立发行版本就该跑自己
的 configure），因此无需 guard。其余 OHOS 适配（config.guess / umask / .la 规避 /
NDEBUG）都在 `conanfile.py` 的构建阶段完成，不碰上游生成文件。

**关闭的可选组件**（`--without-*`）：swig 及 perl/python2/python3/ruby/lua 绑定
（这些绑定全部需要 swig 现生成源码，OHOS 上没有 swig 制品）、gtk-doc（无 gtkdocize）、
valgrind、easy-bindings（连带关闭 `libpreludecpp` C++ 绑定，避免把 C++ ABI 塞进库包）。

## 依赖版本

| 依赖 | 版本 | 用途 | 来源 |
|------|------|------|------|
| gnutls | 3.8.10 | 强制依赖（TLS 会话 / x509 / SRP） | ohpcd 制品仓 ✅ |
| ├ nettle | 3.10.2.1 | gnutls 传递依赖（crypto） | ohpcd ✅ |
| ├ libtasn1 | 4.21.0 | ASN.1 | ohpcd ✅ |
| ├ libgcrypt | 1.11.0 | gnutls 后端 | ohpcd ✅ |
| ├ libgpg-error | 1.55 | libgcrypt 后端 | ohpcd ✅ |
| ├ gmp | 6.3.0 | 大数 | ohpcd ✅ |
| └ libunistring | 1.0 | 字符编码 | ohpcd ✅ |
| automake（tool_requires） | 1.18 | bootstrap（归档无 configure） | ohpcd ✅ |
| libtool（tool_requires） | 2.5.4 | libtoolize + 独立 libltdl 发行版 | ohpcd ✅ |
| autoconf / m4 / perl / flex / bison / clang / make | 2.72 / 1.4.19 / 5.42.0 / 2.6.4 / 3.8.2 / 15.0.4 / 4.4.1 | 宿主 HNP 工具链 | CI 环境内置 |

PCRE 未启用（上游只在 `pcre-config` 存在时开启 substr/regex 判据，可选）。

## 验证结果

```text
$ conan create . -pr=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
libprelude/5.2.0: Running: cd '…/b/tests' && make check
  PASS: async-timer / idmef / idmef-criteria / idmef-message-helper / idmef-path
        idmef-value / prelude-client / prelude-string / prelude-timer
  # TOTAL: 9   # PASS: 9   # SKIP: 0   # FAIL: 0   # ERROR: 0
libprelude/5.2.0: RUN: make install DESTDIR=…/p -j20
libprelude/5.2.0 (test package): RUN: ./test_libprelude
  libprelude 5.2.0 consumer test: OK
```

产物加载自检（test_package 即消费者视角，见 `reports/test-report.md`）：
`libprelude.so.28.1.0` 的 DT_NEEDED = `libgnutls.so.30, libtasn1.so.6,
libgcrypt.so.20, libgpg-error.so.0, libc.so`；SONAME = `libprelude.so.28`。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libprelude.so.28.1.0 | 2,075,136 B | 主库（SONAME libprelude.so.28，含 vendored libmissing/libltdl 目标文件） |
| lib/libprelude.so, lib/libprelude.so.28 | 软链接 | 开发/运行链接 |
| include/libprelude/*.h（48 个） | ~0.5 MB | `#include <prelude.h>` 为总入口（上游 includedir = $(prefix)/include/libprelude） |
| lib/pkgconfig/libprelude.pc | — | 上游 pkg-config 元数据 |
| etc/prelude/default/*.conf（4 个） | — | client/global/idmef-client/tls 配置模板 |
| share/aclocal/libprelude.m4 | — | 下游 autotools 探测宏 |
| licenses/COPYING | — | LGPL-2.1-or-later |
| 合计 | 2.8 MB / 60 个文件 | 包 ID `8921466fcec2cf06aa7c7fdf0b8c6a9c430a15a3` |

## 注意事项

1. **只支持 shared**：上游 `LT_INIT([dlopen win32-dll disable-static])` 不提供静态库，
   配方在 `validate()` 里对 `shared=False` 明确报 `ConanInvalidConfiguration`，
   不做“假静态”。
2. **不发布 CLI**：`bin/prelude-admin`、`bin/prelude-adduser`、`bin/libprelude-config`
   在 package() 中剔除——前两个是 Prelude manager 侧的交互式注册工具（需要活的
   manager/spool 与数据库），`libprelude-config` 已被 pkg-config（`libprelude.pc`）
   取代；本包定位为纯库交付，`cpp_info.bindirs = []`。如后续要把 `prelude-admin`
   作为命令行工具上架，需按 R38 单独补软件级 `commands.json`。
3. **运行环境依赖 gnutls 的 LD_LIBRARY_PATH**：见问题 #10。gnutls 制品的 option 与
   内容不一致属上游包缺陷，修好（重新以 shared=True 发布或补 `.a`）之后本配方里的
   runenv 补偿逻辑可以删掉。
4. `var/spool/prelude` 目录由上游 install 创建（`PRELUDE_SPOOL_DIR`），保留在包里但

   库本身不会写入。
5. **`prelude-timer` 存在时序抖动（已知，未掩盖）**：上游 `tests/prelude-timer.c:34` 的回调
   断言 `elapsed == prelude_timer_get_expire(&timer->timer)` —— 要求「wall-clock 秒差」精确
   等于预期到期值。机器负载高时会 ±1s 抖动。NDEBUG 修复后截至 09-17 16:10 的 8 轮实测：7 轮 9/9 通过，
   1 轮该项以 `Assertion failed: elapsed == prelude_timer_get_expire
   (prelude-timer.c: timer_callback: 34)`（exit 134）失败，证据留存在
   `.conan2/p/b/libpr20ab45afb8f10/b/tests/test-suite.log`（同机另 7 份
   `*/b/tests/test-suite.log` 均为 `# PASS: 9 / # FAIL: 0`，含 W3 采用的
   `libpr530b529caf49b`）。配方把 `cd tests && make check` 作为构建门禁且**不修改上游计时
   断言**（R51：不改上游测试），故 CI 有小概率偶发红灯；命中时按 R42/R44 走
   `submit --resume` + `/rebuild` 重跑即可，不应据此改判为移植缺陷。
   （另见 `reports/test-report.md` 2.5）
6. **包内 `lib/pkgconfig/libprelude.pc` 不可重定位**：Conan 以 `--prefix=/` + `DESTDIR` 安装，
   上游生成的 .pc 里 `prefix=/`、`Libs.private` 还会带构建机的私有绝对 `-L` 路径（与它自己
   批评的 E236 同一形态）。Conan 消费者应使用 `PkgConfigDeps`/`CMakeDeps` 生成的目标
   （配方已 `set_property("pkg_config_name", "libprelude")`），不要直接吃包内这份 .pc。
   本轮为保持「已验证 = 已提交」的一致性未改 `package()`，作为后续清理项登记。
---

**编译结束**: 2026-09-18 22:08
**最终状态**: built
