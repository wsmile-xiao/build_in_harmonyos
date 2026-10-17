# loudmouth 1.5.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-24
- 编译器: clang
- 状态: built

## 编译步骤

loudmouth 是构建在 GLib 之上的轻量 XMPP/Jabber 客户端 C 语言库（维护中的 MCabber fork）。

```bash
# 源码包自带 configure / aclocal.m4（已内嵌 AM_PATH_GLIB_2_0 / PKG_CHECK_MODULES），无需 autoreconf。
./configure --prefix=$PREFIX \
    --with-ssl=no --with-idn=no --with-asyncns=no \
    --disable-shared --enable-static
make -j1
# 上游测试（GLib g_test 框架，4 个用例）：
#   test-parser（2）+ test-data-objects（2），make check 由 gtester 驱动。
```

Conan 配方使用 `AutotoolsToolchain` + `PkgConfigDeps` + `AutotoolsDeps`：
- `PkgConfigDeps` 生成 glib-2.0.pc / gobject-2.0.pc，让 configure 的
  `AM_PATH_GLIB_2_0(2.38.0)` 与 `PKG_CHECK_MODULES(LOUDMOUTH, glib-2.0 gobject-2.0)`
  找到 conan 的 glib。
- OHOS 分支按 E129/E011 处理：`configure --no-create` 生成 config.status 后把
  `umask 077` 改为 `umask 022`，再用 `$CONFIG_SHELL` 执行 config.status
  （HMDFS 对新建目录设 setgid，077 umask 会让临时子目录变成 drwx--S--- 导致
  config.status 写 subs 文件失败）。
- 依赖：glib/2.84.0.1（制品仓对 glib 仅发布 shared 二进制，通过 pkg-config 链入）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 默认 `--with-ssl=gnutls`，设备无 GnuTLS 会 `AC_MSG_ERROR` 硬失败 | 上游 SSL 选项默认 gnutls 且缺失即报错 | 配方 pin `--with-ssl=no`（纯文本订阅是主要场景；idn/asyncns 同 pin 关闭保证确定性） |
| 2 | HMDFS 目录 setgid + umask 077 导致 config.status 写临时文件失败 | E129/E011 平台行为 | `--no-create` + 改 config.status 中 umask 为 022 + CONFIG_SHELL 执行 |
| 3 | 上游测试由 gtester 驱动，OHOS glib 包不保证带 gtester | `make check` 依赖 gtester 二进制 | 配方 build() 内直接执行 test-parser / test-data-objects 两个 GLib 测试二进制（同断言同数据），逐行解析其 `: OK` / `: FAIL` 输出 |
| 4 | 公共头文件装到 `include/loudmouth-1.0/loudmouth/` | 上游安装布局 | `cpp_info.includedirs = ["include/loudmouth-1.0"]`，pc 的 Cflags 与之对应 |
| 5 | 库名含 `-1` 版本后缀 | 上游 `libloudmouth-1` | `cpp_info.libs = ["loudmouth-1"]`，pkg_config_name = "loudmouth-1" |
| 6 | configure 死于 `working directory cannot be determined`（`autotools.configure --no-create` 阶段） | HMBS 平台诊断 [shell_getcwd]：HNP bash 在 HMDFS 构建目录 `getcwd()` 失败，configure 的 `ac_pwd=`pwd`` 检查中止 | 改用 HMBS 注入的 `/bin/sh`（toybox ash，getcwd 正常）执行 configure 与 config.status；删除配方中硬编码的 `/data/service/hnp/bin/bash` 回退；同时预设 `PWD=build_folder` 让 shell 逻辑 pwd 信任有效路径而不调 getcwd(2) |
| 7 | configure 死于 `config.guess: unable to guess system type`（`cannot guess build type; you must specify one`） | 出厂 config.guess（2018-02-24）不识别 `UNAME_SYSTEM="HarmonyOS"`，且配方未传 `--build`/`--host`，configure 需自猜构建类型 | OHOS 分支在 generate() 显式追加 `--build=aarch64-unknown-linux-gnu` 与 `--host=aarch64-unknown-linux-gnu`（标准 GNU 三元组，旧 config.sub 也认），幂等检查避免重复；绕过 config.guess 猜测 |
| 8 | configure 死于 `checking whether we are cross compiling... cannot run C compiled programs`（提示 use --host） | **build==host**（`--build` 与 `--host` 都传了同一个 `aarch64-unknown-linux-gnu`）→ autoconf 判为原生构建（cross_compiling=no），于是去**运行**新编译的 conftest 探针二进制；OHOS 构建沙箱无法执行该 ELF → fatal `cannot run C compiled programs`（captagent/libofa/libncursesada 同款经验） | 只传 `--host=aarch64-unknown-linux-gnu`（**不再传 --build**）→ lone --host 使 cross_compiling=maybe，运行失败 flip 为 yes，跳过运行期探测；config.guess 改为在 build() 预置 `ac_cv_build=aarch64-unknown-linux-gnu` 让 AC_CANONICAL_BUILD 跳过 config.guess（air-quality-sensor/nspr/a52dec 模式）。保留 PWD/SHELL/CONFIG_SHELL 注入与 `--no-create` 分层 |
| 9 | make 阶段 `lm-sasl.c:26:10: fatal error: 'gssapi/gssapi.h' file not found` | loudmouth configure.ac 的 GSSAPI/SASL 是**自动探测**：只要 PATH 里存在 `krb5-config` 就把 `enable_gssapi=yes`、`AC_DEFINE(HAVE_GSSAPI)`，`AM_CONDITIONAL(USE_GSSAPI)` 于是把 `lm-sasl.c` 编进库；而 OHOS 无 krb5 开发头（gssapi/gssapi.h）→ 编译失败。**loudmouth 没有 `--without-sasl` 开关**，仅此探测是唯一门 | build() 的 OHOS 分支预置 `ac_cv_path_KRB5CONFIG=no`（AC_PATH_PROG 的缓存变量），使 configure 跳过 krb5-config 探测 → enable_gssapi=no、USE_GSSAPI 关闭，lm-sasl.c 不再编译 |
| 10 | make 阶段 `make[3]: Leaving directory ... Error 2`（中段被日志摘要截断，具体 .c 报错未展示；可见 configure 输出的 CFLAGS 含 `-Werror`） | loudmouth `IDT_COMPILE_WARNINGS` 在 srcdir 存在 `autogen.sh` 时默认走 `error` 档，向 CFLAGS 注入 `-Werror`。2018 年代码配合全新 glib 2.84 会触发 GLib 弃用 API 告警，`-Werror` 把告警升级为硬错误 → 编译失败（OpenWrt/Gentoo 都因同样原因关掉 -Werror） | 在 generate() 传入 `--with-compile-warnings=no`（IDT_COMPILE_WARNINGS 的标准开关，`no` 档不注入任何 warning flags，含 -Werror），与 Gentoo/OpenWrt 的做法一致；不涉及测试口径 |
| 11 | make 阶段链接 `examples/` 的可执行（lm-register/lm-change-password/lm-send-async/test-lm/test-tunnel/test-http-proxy）报 `ld.lld: error: undefined symbol: g_libintl_gettext`（引用来自 `libloudmouth-1.a` 内 `lm-sock.o` 的 `_lm_sock_addrinfo_get_error_str`） | 库本体（静态 .a）构建不需解析符号，但**链接可执行文件**时必须解析。glib 2.84.0.1 内嵌 proxy-libintl，其 `libintl.h` 无条件把 `gettext` 映射为 `g_libintl_gettext`（glib 私有重命名），该符号由 glib 包自带 `lib/libintl.so` 提供；而 PkgConfigDeps 生成的 glib-2.0.pc 的 Libs 行**不含 `-lintl`**，导致链接可执行时缺符号（libgtop 同款，DRAFT-libgtop-glib-libintl-link） | 沿用 libgtop/2.41.3 已验证模式：OHOS 分支在 generate() 内当 glib 包 libdir 真实存在 `libintl.so` 时，向 configure_args 追加 `LDFLAGS=-L{glib_libdir} -lintl -Wl,-rpath,{glib_libdir}`（写入所有 Makefile 链接行，覆盖 examples/tests；rpath 让构建期可执行及 conftest 运行时定位 libintl.so.8）；并在 package_info 的 OHOS 分支把 `cpp_info.libs` 改为 `["loudmouth-1","intl"]`，让消费方（test_package/下游）链接时也带 `-lintl`（glib 的 -L 可解析）。guard 仅在 libintl.so 真实存在时注入，绝不虚构路径 |

## 源码修改

无补丁（上游源码零改动，仅配方层适配）。

## 依赖版本

- glib/2.84.0.1（glib-2.0 + gobject-2.0）

## 验证结果

- 上游测试（GLib g_test，gtest_macros 口径）：test-parser 2 用例 + test-data-objects 2 用例 = 4。
  在 HarmonyOS aarch64 环境通过 conan create 预检真实执行，结果见 PR「上游测试用例通过率」。
- test_package（test.c，8 项真实 loudmouth API 断言）：连接构造/状态、message 节点构造与 XML 序列化。
  （第 6 轮修复：原第 1 条断言的 `loudmouth_get_version()` 在该 fork 并不存在，已删除，见下方轮次记录。）

## 注意事项

- `loudmouth/Makefile.am` 的 `test-dns` 是 noinst_PROGRAMS 辅助程序，未接入
  `make check`/`TEST_PROGS`，不计入注册测试总数（R51 审计已注明）。
- SSL 关闭后的库仍可正常构造连接与解析 XML stanza（测试覆盖该路径）。

## 第 2 轮修复：上游测试结果解析器（parsed 0 vs audited 4）

真机预检在**已成功编译并链接全部目标**（ar/ranlib 生成 libloudmouth-1.a、test-dns 链接完成）后失败：

```
loudmouth/1.5.4: ERROR: Invalid configuration: upstream test harness drift:
parsed 0 cases but audited 4; refusing to certify.
== test-parser exit=0 ==
TAP version 14
# random seed: R02Saa...
ok 2 /parser/invalid/suite
== test-data-objects exit=0 ==
TAP version 14
# random seed: R02Sb...
1..2
ok 1 /data_objects/auth_paramters
ok 2 /data_objects/connect_parameters
```

**根因**：编译构建全部成功，测试二进制也真实运行且全部通过（`ok` 行），但旧 `_run_upstream_tests` 只按**旧版 g_test 输出** `path: OK` / `path: FAIL` 计数。对着 OHOS 仓 glib 2.84 的 g_test 默认 **TAP 输出**（`TAP version 14`、`1..N` 计划行、`ok N /path` / `not ok N /path`），一条都匹配不上 → parsed 0，触发 audited=4 的漂移守卫。（该守卫反而证明测试确实执行了、只是被解析器漏数，并非静默跳过/伪造。）

**修复**：`_run_upstream_tests` 增加 TAP 解析：
- `ok` / `ok N <path>` → passed
- `not ok` / `not ok N <path>` → failed
- 仅当某个测试程序完全没输出 TAP 结果行时，才回退到旧 `: OK` / `: FAIL` 格式（避免同一用例双重计数）。
- `discovered = passed + failed`（取自真实输出），仍强制 `== UPSTREAM_TESTS_TOTAL(4)`；`executed = discovered`。
- 本地模拟真实日志输入验证：discovered=4、passed=4、failed=0。

**可复用经验**：GLib g_test 二进制直接运行（无 gtester 包裹）时，GLib ≥2.7 默认输出就是 **TAP** 而非旧版 `path: OK`。任何基于 GLib 的配方在解析测试结果时都应优先认 TAP 的 `ok`/`not ok` 行；TAP 计划行 `1..N` 与注释行 `#...` 不计入用例数。

## 第 3 轮修复：`make install` 多源 install `Error 64`（package() 阶段）

TAP 计数修复后，真机已 4/4 通过上游测试并成功 `make`，但**进入 package() 的 `make install` 时失败**：

```
make[4]: *** [Makefile:686: install-libloudmouthincludeHEADERS] Error 64
 /storage/.../runtime/loudmouth-1.5.4/bin/install -c -m 644
   .../b/loudm49d17ee5d2eff/b/loudmouth/lm-connection.h ... loudmouth.h
   '.../p//include/loudmouth-1.0/loudmouth'
```

**根因**：旧版 automake 的 `install-libloudmouthincludeHEADERS` 把全部 9 个公共头文件**放在同一条 `$(INSTALL_DATA)` 命令**里（`install -c -m 644 f1 f2 ... f9 destdir`，多源形式）。真机上的 HMBS/toybox `install`（位于 `runtime/.../bin/install`）对**多源 install 返回 Error 64**（单文件 install——静态库、.pc——正常，所以库与 .pc 已先安装成功）。这是 E596/openfst 与 DRAFT-libnih 记载的同一设备端 install 多源缺陷。

**修复**（沿用 E596 / libnih 已验证模式，配方的 `_patch_install_for_hmfs`）：
- 在 `package()` 里写一个多源兼容的最小 `install` shim（`/bin/sh hmbs-install-shim.sh`）：解析 `-c / -m MODE / -d` 并剥离，剩余参数按「文件们 + 目标目录」或「单文件 + 目标完整路径」处理，用普通 `mkdir -p` + `cp -f` 逐个复制，`chmod` 不存在时静默跳过（HMFS `chmod:0`）。
- `os.walk(self.build_folder)` 递归所有生成的 `Makefile`，用正则把 `INSTALL = <任何值>` 改写为 `INSTALL = /bin/sh <shim 绝对路径>`。`INSTALL_DATA`/`INSTALL_PROGRAM` 引用 `${INSTALL}`，随主变量自动重算 → 全库/头安装都走 shim。
- 关键纪律（来自 E596/libnih）：**不**经 make 命令行传 `INSTALL_DATA=$(INSTALL)`（bash 命令替换吃空参数 → Error 126）；**不**靠 PATH 前置覆盖；改的是 Makefile 内变量。
- `Autotools(self).install()` 仍只管 `make install`，文件落到 `package_folder`（DESTDIR 语义不变）；随后原有的删除 `.la` 逻辑不变。
- 上游测试计数口径不变（test-parser 2 + test-data-objects 2 = 4，TAP 解析）。

**可复用经验**：configure 时代的 autotools 工程若用多文件 `$(INSTALL_DATA) f1..fN destdir` 安装头文件，而在 HMDFS 真机上 install 报 Error 64（单文件正常），配方在 `package()` 里把各 Makefile 的 `INSTALL` 改写指向自写多源 shim（`/bin/sh` 调用，`cp`/`mkdir` 可用）即可，无需改测试口径。

## 第 4 轮修复：test_package CMakeDeps 消费失败 `Library 'intl' not found in package`

第 3 轮 install shim 修复后，真机库本体与上游测试全部成功（built + 4/4 passed），但**包生成后的 test_package（CMake 消费方）configure 失败**：

```
CMake Error at .../generators/cmakedeps_macros.cmake:81 (message):
  Library 'intl' not found in package.  If 'intl' is a system library,
  declare it with 'cpp_info.system_libs' property
Call Stack:
  .../loudmouth-Target-release.cmake:23 (conan_package_library_targets)
ERROR: loudmouth/1.5.4 (test package): Error in build() method, line 32
    cmake.configure()
```

**根因**：`package_info` 的 OHOS 分支把 `cpp_info.libs` 设成 `["loudmouth-1", "intl"]`。CMakeDeps（test_package 的 CMake 生成器）把 `cpp_info.libs` 里的每一项都当作**包内提供的库文件**，生成 `conan_package_library_targets` 时去包内找 `libintl.so`；而 `intl` 并不在 loudmouth 包内，它解析自 glib 私有 libdir（glib pc 的 -L / CMakeDeps 对 glib 组件的链接目录传播）。于是 configure 报 `Library 'intl' not found in package`。pkg-config 消费路径没问题（glib 的 -L 在 Libs 行），但 CMakeDeps 消费路径会在 configure 期直接 abort。

**修复**（按 CMakeDeps 报错提示）：把 `intl` 从 `cpp_info.libs` 移到 `cpp_info.system_libs`（追加到已有的 `["dl","pthread","m"]`）：

```python
if self.settings.os == "OHOS":
    self.cpp_info.system_libs = ["dl", "pthread", "m", "intl"]
    self.cpp_info.libs = ["loudmouth-1"]
```

CMakeDeps 对 `system_libs` 的处理是向消费方链接行直接发 `-lintl`（不要求包内文件），链接时经消费方链接搜索路径（含 glib 的 -L）解析，与 pkg-config 的 `-lintl` 语义一致。这是 CMakeDeps 的标准机制；声明为 system library 恰好是错误信息明确指出的正确做法。

**可复用经验**：当某库链接的符号由**依赖包的私有 libdir** 提供（如 glib 内嵌 proxy-libintl 的 `g_libintl_gettext`），但库本体 / 本包并不随附该 `.so` 时，**绝不能**把这个库放进 `cpp_info.libs`（CMakeDeps 会要求包内文件 → configure 期 `Library 'X' not found in package`）。应放入 `cpp_info.system_libs`，让 CMakeDeps 生成 `-lX` 而非去包内找文件。

## 第 5 轮修复：test_package CMake 编译 `fatal error: 'glib.h' file not found`

intl → system_libs 修复后（configure 通过），test_package 的 **build（编译 test.c）** 失败：

```
In file included from .../p/include/loudmouth-1.0/loudmouth/lm-connection.h:26:
In file included from .../p/include/loudmouth-1.0/loudmouth/lm-message.h:26:
.../p/include/loudmouth-1.0/loudmouth/lm-message-node.h:26:10: fatal error: 'glib.h' file not found
#include <glib.h>
         ^~~~~~~~
1 error generated.
ERROR: loudmouth/1.5.4 (test package): Error in build() method, line 33
    cmake.build()
```

**根因**：loudmouth 的**已安装公共头文件**（lm-connection.h / lm-message.h / lm-message-node.h …）`#include <glib.h>`，即 glib 的头文件是 loudmouth **公开接口**的一部分。但 `requirements()` 里 `self.requires("glib/2.84.0.1")` **没有声明 `transitive_headers=True`**（Conan 2 默认 false）。于是 CMakeDeps 生成的 `loudmouth::loudmouth` 目标的 `INTERFACE_INCLUDE_DIRECTORIES` **不含 glib 的 include 目录**，消费方编译任何 include 了 loudmouth 头的 TU 都找不到 `glib.h`。

主库 autotools 构建靠 pkg-config（PkgConfigDeps）的 Cflags 拿到 glib include 而正常，所以编译/上游测试都过，**只有 CMake 消费方（test_package）踩中**。仓库内所有在公共头暴露 glib 的库（atk/evince/cairo/ayatana-* 等）都对 glib 声明了 `transitive_headers=True, transitive_libs=True`，这是既定模式。

**修复**：`requirements()` 改为：

```python
self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
```

`transitive_headers=True` 让 glib 的 include 目录注入 `loudmouth::loudmouth` 接口；`transitive_libs=True` 让静态 loudmouth 的消费者链接 glib 库（与其余 glib 库配方一致）。只影响下游消费方传播，不影响主库 autotools 自身构建（其仍走 pkg-config）。

**可复用经验**：若某库的**公共安装头文件** `#include` 某个依赖的头，则该依赖在 `requires()` 里必须带 `transitive_headers=True`（且通常 `transitive_libs=True`），否则 CMakeDeps 消费方编译会报该依赖头 `file not found`；此错误只在 CMake 消费路径暴露（pkg-config 路径靠 Cflags 掩盖）。

## 第 6 轮修复：test_package 编译 `loudmouth_get_version` 隐式 int（无此 API）

transitive_headers 修复后（glib.h 找到），test_package 的 **build（编译 test.c）** 报：

```
test_package/test.c:58:18: error: incompatible integer to pointer conversion
passing 'int' to parameter of type 'const char *' [-Wint-conversion]
          strlen(loudmouth_get_version()) > 0,
```

**根因**：测试程序断言 1 调用了 `loudmouth_get_version()`，并把它当字符串传给 `strlen()`。但 **mcabber fork 的 loudmouth 1.5.4 根本没有这个函数**——审查 1.5.4 源码公共头（loudmouth.h 汇总头 / lm-utils.h 只声明 `lm_utils_get_localtime` / lm-connection.h 只有 `lm_connection_*` / lm-message*.h 只有 `lm_message*`）均无 `loudmouth_get_version` 声明。于是 clang 把它当作未声明的隐式声明，默认返回 `int`，再传给 `strlen(const char *)` 就报 int→pointer 转换错误。（老版本 loudmouth 曾有 `loudmouth_get_version()`，但此 fork 已移除；测试早期按惯性写了该假想 API。）

**修复**：从 test.c 删除这条不存在的 API 调用及其断言。其余 8 条断言全部是经核实的真实 loudmouth 公开 API：`lm_connection_new` / `lm_connection_get_state` / `lm_connection_unref` / `lm_message_new` / `lm_message_get_node` / `lm_message_get_type` / `lm_message_node_set_attribute` / `lm_message_node_to_string`（+ XML 内容校验）。`lm_connection_new` 本身即验证了库链接/符号解析（跑通即说明符号可链接），断言 1 的原意已被覆盖。同步把 test_package 断言计数从 9 改为 8，并更新 MANIFEST.yml 的 `assertion_count: 8` / `test_package_tests` 描述，以及 `.hmbs/pr-body.md` 草稿的「新增测试 8」「合计 12」「8/8」。

**可复用经验**：为库补写 test_package 断言时，**必须**对照该 fork/tag 的真实公共头确认 API 存在与签名；不要沿用老版本/其他 fork 的 API 名（如 `loudmouth_get_version` 在新 loudmouth 已移除）。编译器把未声明函数当作隐式 `int` 并报「incompatible integer to pointer conversion」时，几乎总是调用了不存在的 API。删除不存在的断言不算伪造通过——其余断言仍真实执行；同时把声明的断言总数同步到 MANIFEST.yml（`assertion_count`）与 PR 正文。


## 第 7 轮修复：test_package 校验 pc 文件名错误（PACKAGE_VALIDATION missing=['lib/pkgconfig/loudmouth-1.pc']）

库本体与上游测试（4/4）均随前几轮通过，本轮真机失败发生在 package() 成功后的
**test_package 的 test() 阶段**：

```
ERROR: loudmouth/1.5.4 (test package): Error in test() method, line 45
	ConanException: PACKAGE_VALIDATION missing=['lib/pkgconfig/loudmouth-1.pc']
```

**根因**：test_package 的 `test()` 硬编码校验包内存在 `lib/pkgconfig/loudmouth-1.pc`，
但上游 `make install` 实际安装的 pkg-config 模块文件名是 **`loudmouth-1.0.pc`**
（Makefile.am `pkgconfig_DATA = loudmouth-1.0.pc`，源自 `loudmouth-1.0.pc.in`）。
配方 package_info 里的 `pkg_config_name = "loudmouth-1"` 只是这仓库的 Conan 属性，
供 PkgConfigDeps 在**依赖侧**生成消费者 .pc，并不重命名包内已安装的上游 pc 文件。
于是头文件与 lib 都校验通过，唯独 pc 用错了名字 → 报 missing。

**修复**：把 test_package 校验项从 `lib/pkgconfig/loudmouth-1.pc` 改为上游真实安装名
`lib/pkgconfig/loudmouth-1.0.pc`（并在代码注释 + README 注明 loudmouth-1 vs loudmouth-1.0
两个名字的语义，避免再混用）。同步修正 archives/l/loudmouth/README.md 的产物说明。
test_package 的 CMakeLists 仍用 `find_package(loudmouth)`（Conan 生成 target），不读 .pc，
故校验只作打包完整性检查，改文件名不影响测试执行与断言口径（8 项断言不变）。

**可复用经验**：为 autotools 库做 test_package 打包校验时，`lib/pkgconfig/<模块>.pc`
的实际文件名必须查上游 `Makefile.am` 的 `pkgconfig_DATA`（常带版本后缀，如
loudmouth-1.0.pc），而不是想当然用 Conan `pkg_config_name`（那只是依赖侧生成名）。
