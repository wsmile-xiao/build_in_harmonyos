# avahi-compat-libdns_sd 0.9_rc5 适配笔记

## 概述

- **软件**：avahi-compat-libdns_sd（Avahi 项目的 Bonjour 兼容层，产出 libdns_sd）
- **版本**：0.9_rc5（上游 tag `v0.9-rc5`，OpenWrt/Homebrew 均使用同一归档）
- **官方源**：https://github.com/avahi/avahi/archive/refs/tags/v0.9-rc5.tar.gz
- **sha256**：`5b0a9d88110b0fc8aaafc5cc0a26e83e7d2a4aca3a36bc27c9b626db7ead27b0`
  （本机实测下载校验一致；OpenWrt PKG_HASH 与 Homebrew 公式同值）
- **许可证**：LGPL-2.1-or-later
- **构建系统**：Autotools

## 上游结构调查

- `avahi-compat-libdns_sd/` 是 avahi 源码树的一个子目录，`Makefile.am` 中：
  - `lib_LTLIBRARIES = libdns_sd.la`，源文件 `dns_sd.h compat.c txt.c unsupported.c warn.c warn.h`
  - 链接 `../avahi-common/libavahi-common.la` 与 `../avahi-client/libavahi-client.la`
  - 条件 `if HAVE_DBUS / if ENABLE_COMPAT_LIBDNS_SD`（需要 dbus 且开启 compat）
  - 测试 `TESTS = txt-test null-test`（`--enable-tests` 下构建）
- configure.ac 关键开关：
  - `--enable-compat-libdns_sd`、`--enable-tests`（默认关闭）
  - `--with-distro=none`（OHOS 上 `uname -s`=Linux 会触发 distro 探测错误）
  - `--disable-glib/gobject/libevent/qt3/4/5/gtk/gtk3/python/mono/manpages/xmltoman/gdbm/libdaemon`
  - `--enable-compat-libdns_sd` 要求 `BUILD_CLIENT`（avahi-client），而 client 依赖 dbus
- 上游测试均为纯输入/编码测试：
  - `txt-test.c`：TXTRecordCreate/SetValue/ContainsKey/GetValuePtr 编码解码往返
  - `null-test.c`：DNSServiceRegister/Browse 的 NULL 引用与非法 regtype 校验
  - 两者都不需要运行中的 avahi 守护进程，真机可直接执行

## 适配要点

1. **bootstrap**：GitHub tag 归档不含 configure，`build()` 先 `NOCONFIGURE=1 bash autogen.sh`
   生成 configure，再 `bash configure ...` 显式执行（绕开 OHOS 脚本执行限制）。
   构建期工具：automake/1.18、libtool/2.5.4、gettext/0.22.5.1 走 tool_requires
   （autoconf/m4 由 SDK `/data/service/hnp/bin` 提供，参考 accel-config 配方做法）。
2. **dbus 依赖**：avahi-client 需要 dbus 头文件与 `dbus-1.pc`；dbus 的 Conan 包
   未安装 `.pc` 文件，`generate()` 中从 dbus 包目录生成 `dbus-1.pc` shim 并
   前置到 `PKG_CONFIG_PATH`，满足 configure 的 `PKG_CHECK_MODULES(DBUS, [dbus-1 >= 0.34])`。
3. **裁剪构建**：顶层 `make` 会构建 avahi-daemon/core/utils（需要 libdaemon、expat、
   gdbm 等），因此只按依赖顺序 `make -C avahi-common` → `make -C avahi-client` →
   `make -C avahi-compat-libdns_sd`，再 `make -C avahi-compat-libdns_sd check` 跑上游测试。
4. **打包**：libdns_sd 静态链接 avahi-common/avahi-client，三个库及其头文件一起安装，
   `cpp_info.libs = ["dns_sd", "avahi-client", "avahi-common"]`，
   `cpp_info.requires = ["dbus::dbus"]`（静态链接需要 dbus 符号）。
5. **上游测试接入**：`make -C avahi-compat-libdns_sd check` 输出 automake 测试汇总，
   解析 PASS/FAIL/SKIP 后输出 `HMBS_UPSTREAM_TEST_RESULT` 标记（discovered=2 预期）。
6. **test_package**：`test.c` 真实调用 libdns_sd 的 `TXTRecord*` API 与
   `DNSServiceRegister` 非法 regtype 校验（10 个断言），输出 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 真机预检预期

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`
- 预期上游标记：`HMBS_UPSTREAM_TEST_RESULT` status=passed, discovered=2, executed=2
- 预期 test_package 标记：`HMBS_TEST_PACKAGE_RESULT` discovered=10, passedCount=10
- 数字以真机实际输出为准，本笔记不预先填写。

## 潜在风险

- autogen.sh 需要 gettextize（gettext 包提供），若真机环境缺该工具需调整 tool_requires
- dbus/1.14.10 若尚未发布到制品仓，conan create 会失败，需先发布 dbus
- `--host=aarch64-unknown-linux-gnu` 与 config.guess 的 OHOS 识别若冲突，
  参考 libx11 先例以该 triplet 显式指定即可

## 本轮（R17 真机预检失败修复：cmake/4.4.2 KeyError 'OHOS'）

- 失败阶段 compile。两个信号：
  1. `preflight.sh[229]: can't create temporary file /tmp/shbdc7pr.tmp: Read-only file system` ——
     hmbs 包装脚本自身 mktemp 探测的噪声（preflight.sh 第 229 行硬编码 /tmp），非致命；
     已对 avahi 配方目录 grep 审计 `/tmp|mktemp|tempfile|TMPDIR` 零命中，配方无 /tmp 写入，不改。
  2. `cmake/4.4.2: Error in build() method ... KeyError: 'OHOS'` —— 真实失败。
- 根因：预检 remote 顺序 conancenter 在前，`dbus/1.14.10`（本仓配方）传递 `expat/2.8.2`，
  同版本解析到 conancenter 上游配方；其依赖树 tool_require `cmake/4.4.2`，该 cmake 配方
  build() 按 `conan_data["sources"][version][os][arch]` 取预编译包，OHOS 无键 → KeyError。
  与 libgsf/pycairo 记录过的坑完全同型（经验 1）。
- 修复：`requirements()` 增加 `self.requires("expat/2.8.2.1", override=True)`——
  2.8.2.1 为仓库独有已发布版本（conancenter 无同版本，fontconfig/2.18.1.1、goffice、ice、
  exiv2、vips 均消费），自动解析到 ohpcd 本仓适配配方（裸 cmake + SDK toolchain，无 conan
  cmake tool_require），cmake/4.4.2 整体移出依赖图。manifest.yaml dependencies 同步注明。
- test_package 无需改：仅 requires tested_reference_str，override 图级生效。
- python -m py_compile 通过。仅工作树修改，未 commit/push。

## 本轮（R18 真机预检失败修复：源码下载超时 + HNP bash 无法 getcwd）

失败阶段 compile，真机日志两个根因：

1. **源码下载直连超时**：`HTTPSConnectionPool(host='github.com', port=443): ConnectTimeoutError ... connect timeout=30`，
   仅靠 conan 重试成功（"Sources correctly downloaded"）。按仓库 ci/conan/build_and_test.sh 的
   github 镜像规则（gh-proxy.com 前置、官方 URL 兜底）将 conandata.yml 的 url 改为有序列表，
   sha256 保持官方原值 5b0a9d88...，不因镜像改校验值（经验 1 apply）。
2. **编译失败（build() autogen.sh 行）**：`shell-init: error retrieving current directory:
   getcwd: cannot access parent directories: Not supported` + `pwd: error retrieving current
   directory` —— HMFS/HMDFS 工作目录下 HNP bash 启动即 getcwd 失败。HMBS 平台诊断
   `[shell_getcwd]` 明确要求：使用 HMBS 已注入的 SHELL=/bin/sh 和 CONFIG_SHELL=/bin/sh，
   不要在配方中硬编码 /data/service/hnp/bin/bash。

修复（E330/E232 同款思路，仅工作树，未 commit/push）：
- conanfile.py build()：`bash autogen.sh`/`bash configure`/`bash -c "make check"`
  全部改为 `shell = CONFIG_SHELL or SHELL or /bin/sh` 显式解释执行，并同步注入
  CONFIG_SHELL/SHELL 环境（autoconf 重新执行与 automake 内部 $(SHELL) 均落到 /bin/sh）。
- test_package/conanfile.py：`os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")`
  改为 CONFIG_SHELL/SHELL 优先、/bin/sh 兜底，去掉硬编码 bash 路径。
- 已核实上游 autogen.sh（v0.9-rc5）shebang 为 `#!/usr/bin/env bash`，但只用 local/$()/set -e
  等 mksh/ash 兼容语法，/bin/sh 解释可执行；configure 由 autoconf 生成，显式经 sh 执行无碍。
- python -m py_compile 通过；conandata.yml yaml.safe_load 验证 url 为长度 2 的列表。

## 本轮（R19 真机预检失败修复：gettextize: *** Stop.）

- 失败阶段 compile，build() 第 142 行 autogen.sh 内 gettextize 报
  `gettextize: *** Stop.`（首行错误消息被日志省略）。
- 根因：avahi autogen.sh 用 `sed 's/read dummy/\#/' $(which gettextize) | sh -s -- --copy --force`
  调用 gettextize；gettext 0.22.5 的 gettextize.in 首部 `: ${gettext_datadir="@datadir@/gettext"}`
  把数据目录硬编码为 gettext 制品**构建机**的绝对路径（@datadir@ 构建期展开），Conan 制品
  可重定位，预检机 conan-home（/storage/Users/currentUser/preflight/clients/745d7114f500/
  conan-home）与构建机不同 → baked 路径不存在 → gettextize 第 398 行
  `cd "$gettext_datadir" || func_fatal_error` 失败，打印
  `*** gettext source directory '<构建机路径>/share/gettext' doesn't exist` + `*** Stop.`
- 复现：本机用 gettext-0.22.5 官方 gettextize.in（模板替换 + 假 aclocal/autom4te）对
  avahi v0.9-rc5 源码树模拟完整执行，精确复现该错误；设置 gettext_datadir 环境变量后
  gettextize 完整跑通（exit 0），正常复制 ABOUT-NLS/config.rpath/po/Makefile.in.in 等。
- 修复：conanfile.py generate() 中从 tool_require gettext 包取 package_folder，注入
  `gettext_datadir=<pkg>/share/gettext`（gettextize 支持该环境覆盖）与
  `ACLOCAL_PATH=<pkg>/share/aclocal`（gettext 的 gettext.m4/iconv.m4 等 aclocal 宏所在，
  gettextize 的 m4 复制源 @datadir@/aclocal 同样是 baked 路径、不可用，aclocal 经
  ACLOCAL_PATH 直接找到宏）。目录不存在时仅告警不阻断（诚实暴露布局异常）。
- 上游 autogen.sh 无需打补丁；仅工作树修改，未 commit/push。
- python -m py_compile 通过。

## 本轮（R20 真机预检失败修复：configure 找不到 libexpat）

- 失败阶段 compile，build() configure 行：
  `checking for XML_ParserCreate in -lexpat... no` / `-lbsdxml... no` →
  `configure: error: *** neither libexpat not libbsdxml could be found ***`。
- 根因：avahi configure.ac（v0.9-rc5）在 `--with-xml` 未指定（默认空）时进入
  else 分支，强制要求 expat 或 bsdxml（AC_CHECK_LIB 链接探测）。配方只构建
  avahi-common/avahi-client/avahi-compat-libdns_sd，XML 仅被 avahi-daemon 使用
  （configure.ac:1229 BUILD_DAEMON 依赖 HAVE_XML && HAVE_LIBDAEMON），三个子目录
  Makefile.am 均无 XML_CFLAGS/HAVE_XML 引用。expat 需求（override 2.8.2.1）仅
  服务于 dbus 传递依赖图，配方本身不需要 expat 符号。
- 修复：`_configure_args()` 增加 `--with-xml=none`（configure.ac:722 显式支持，
  直接跳过错误分支）。不改 expat override（dbus 依赖仍需要它避免 conancenter
  cmake/4.4.2 KeyError，R17 修复保留）。
- python -m py_compile 通过。仅工作树修改，未 commit/push。

## 本轮（R21 真机预检失败修复：configure 找不到 libsystemd）

- 失败阶段 compile，configure 报：
  `checking for  libsystemd ... no` →
  `configure: error: Package requirements ( libsystemd ) were not met: No package 'libsystemd' found`。
- 根因：avahi configure.ac 中 `AC_ARG_ENABLE(libsystemd)` 默认值为 yes
  （configure.ac:825 `[HAVE_LIBSYSTEMD=yes]`），未显式关闭时必然执行
  `PKG_CHECK_MODULES(LIBSYSTEMD, [libsystemd])`（configure.ac:828），OHOS 无
  systemd 的 pkg-config → 硬失败。libsystemd 仅用于 avahi-daemon 的 systemd
  集成（notify/watchdog），本配方不构建 daemon。
- 修复：`_configure_args()` 增加 `--disable-libsystemd`（configure.ac:819 显式
  支持该开关 → HAVE_LIBSYSTEMD=no 跳过 PKG_CHECK_MODULES）；同时加
  `--with-systemdsystemunitdir=no` 防止 configure.ac:1140 的
  `$PKG_CONFIG --variable=systemdsystemunitdir systemd` 默认探测。
- 审计后续检查：python/mono/monodoc 均已显式 disable（monodoc 的
  PKG_CHECK_MODULES 被 HAVE_MONO=no 短路），dbus 检查此前已通过
  （真机日志已越过 dbus 检查到达 libsystemd），无后续硬失败点。
- python -m py_compile 通过。仅工作树修改，未 commit/push。

## 本轮（R22 真机预检失败修复：config.status mktemp 临时目录 Permission denied）

- 失败阶段 compile，configure 收尾阶段报：
  `./config.status[1324]: can't create ./confbmSnyt/subs1.awk: Permission denied` →
  `config.status: error: could not setup config files machinery`。
- 根因（E112/E118/E011，与 aaphoto/abiword/acct 同型）：HMFS 上 toybox `mktemp -d`
  创建的临时目录为 drwx--S---（2700 + setgid），HMFS 安全机制拒绝后续写入 subs*.awk；
  Autoconf AS_TMPDIR 首选 mktemp，命中该受限目录即硬失败。avahi 归档不含 configure
  （由 autogen.sh 生成），无法像 aaphoto 那样打 configure 补丁。
- HMBS 平台诊断 [unsafe_local_mktemp] 指定修法：当 HMBS_AUTOCONF_MKTEMP_FALLBACK=1
  时，仅在 configure 阶段让 mktemp 返回失败，触发 Autoconf 的 mkdir fallback
  （acct/6.6.4 已验证通过的同源方案）。
- 修复（仅工作树，未 commit/push）：
  - conanfile.py 新增 `_mktemp_fallback_env()`：检测 HMBS_AUTOCONF_MKTEMP_FALLBACK=1
    时在 build_folder 生成 `mktemp-shim/mktemp`（`#!/bin/sh` + `exit 1`，chmod 0o755
    失败仅告警），并以 Environment.prepend_path("PATH", shim_dir) 保存
    `avahi_mktemp_env` 环境脚本。
  - build() 中仅 configure 一次 self.run 追加该 env 脚本（configure_env），
    autogen.sh 与 make 保持原 env，不受 mktemp shim 影响，最小化改动范围。
- python -m py_compile 通过；AST 校验通过。

## 本轮（R23 真机预检失败修复：R22 shim 方案无效，改用文本 patch 生成的 configure）

- 失败阶段 compile，错误与 R22 同指纹：
  `./config.status[1324]: can't create ./confX6RKzG/subs1.awk: Permission denied` →
  `config.status: error: could not setup config files machinery`。
- R22 的 PATH mktemp shim 方案无效，证据：
  1. `HMBS_PLATFORM_CAPABILITIES` 明确 `"chmod":0`——HMFS 忽略 chmod，shim 文件
     不可执行，PATH 命中 shim 也不会运行，真实 mktemp 仍被调用（错误中的目录名
     `confX6RKzG` 即真实 mktemp 生成的 `confXXXXXX` 展开）。
  2. 即使 shim 生效，Autoconf mkdir fallback 行本身仍是 `(umask 077 && mkdir "$tmp")`
     （autoconf 拼写为 `umash 077 && mkdir`），在 HMFS 上同样生成 2700+setgid
     目录，依旧 Permission denied。所以"让 mktemp 失败"路线不可行，改为直接消除
     `umask 077`。
- 本轮修复（仅工作树，未 commit/push）：
  - 删除 `_mktemp_fallback_env()` 及 build() 中的 configure_env shim 注入。
  - 新增 `_patch_generated_configure()`：autogen.sh 生成 configure 后、运行 configure
    前，用 re.subn 把 configure 中所有 `umask 077 && mktemp -d` / `umask 077 && mkdir`
    前缀删除（正则 `um(?:ask|ash) 077 && ...` 同时覆盖 autoconf 的 `umash` 拼写错误；
    替换的是 configure 本体与内嵌 config.status heredoc 模板两处，heredoc 内 `\$tmp`
    转义形态同样命中）。
  - mktemp 不再受 umask 077 限制 → 默认 umask 创建可写目录，config.status 可写入
    subs*.awk（aaphoto/abiword/acl/abnfgen 同款思路；本库 configure 为 autogen
    动态生成，无法用归档补丁，故在 build() 内文本 patch）。
  - 自检：py_compile 通过；两种 autoconf 形态（`./confXXXXXX` 与 `$TMPDIR/confXXXXXX`）
    及 heredoc 转义形态 fixture 全部命中且 `umask 077` 残留为零。

  ## 本轮（R24 真机预检失败修复：make install 批量头安装 exit 64 EX_USAGE）

  - 失败阶段 compile（`package()` 第 276 行 `make -C avahi-common install`）：
    `make[1]: *** [Makefile:1545: install-avahi_commonincludeHEADERS] Error 64`，
    具体命令为
    `/.../runtime/avahi-compat-libdns_sd-0.9_rc5/bin/install -c -m 644 strlst.h
    address.h alternative.h domain.h cdecl.h defs.h malloc.h watch.h timeval.h
    simple-watch.h thread-watch.h gccmacro.h error.h llist.h rlist.h
    '.../p/include/avahi-common'` —— 14 个头文件一次批量拷贝。
  - 根因（E182/E188 同型，adms 2.3.7 / libgsf 1.14.58 / xeyes 1.3.1 已过门禁先例）：
    HMBS 的 install shim（`runtime/<task>/bin/install`）只接受单文件两参调用，
    automake 的 `install-<dir>HEADERS` 规则用 `$(INSTALL_DATA) $$files destdir`
    一次批量安装（avahi-common 14 个、avahi-client 3 个头文件）→ 多源调用
    直接 exit 64 (EX_USAGE)。库安装（libtool 单文件逐次 install + ranlib）不受影响，
    与日志中 .a 安装成功、仅头文件安装失败吻合。
  - 修复（仅工作树，未 commit/push，xeyes/adms/libgsf 同款方案）：
    - 新增 `_write_install_shim()`：在 build_folder 写 `_ohos_install_shim/install`
      cp/mkdir shim——解析 `-c/-m/-d` 等选项、末参为目标（目录或文件）、逐源
      `cp -f` 复制、chmod 容错跳过（HMFS 不支持 chmod，HMBS_CAP_CHMOD=0）；
      用 `os.open(..., 0o755)` 按 open mode 直接给执行权限（HMFS 忽略 chmod）。
    - 新增 `_redirect_install_to_shim()`：walk source_folder 下所有生成 Makefile，
      把 `INSTALL = <...>/install ...` 行替换为 `INSTALL = <shim>`；
      INSTALL_DATA/INSTALL_PROGRAM 为 `${INSTALL} -m 644`/`${INSTALL}`，
      引用自动重算，make install 全程走 shim。
    - `package()` 在 install 循环前先写 shim 并重定向三个子目录的 Makefile。
  - 自检：py_compile 通过；ast 提取真实 shim 脚本本地实测多源/单文件/-d 三种
    调用形态全部成功；重定向函数对 fixture Makefile（含 runtime install 路径）
    替换正确、INSTALL_DATA/PROGRAM 未动、幂等。

## 本轮（R25 CI 失败修复：test_package 链接 g_libintl_* 未定义符号）

- 失败阶段 test_package（CI #29369），conan create 的 test_package 构建报：
  `old.lld: error: undefined symbol: g_libintl_bindtextdomain` /
  `g_libintl_bind_textdomain_codeset`，referenced by
  `libavahi_common_la-i18n.o:(avahi_init_i18n) in .../libavahi-common.a`，
  clang-15 链接 test_dns_sd 失败 → conan create failed。
- 根因：主包静态库 avahi-common 的 i18n.o 在 ENABLE_NLS 下调用
  bindtextdomain/bind_textdomain_codeset，头文件映射为 g_libintl_* 符号
  （gettext libintl 库）；OHOS/bionic 无 libintl，静态库消费方最终链接时
  符号无法解析。主库本身 .a 归档阶段不解析符号，故 configure/make 均通过，
  只有 test_package 链接阶段暴露。
- 上游证据：avahi-common/i18n.h 在 `#ifdef ENABLE_NLS` 下才 include
  <libintl.h> 并定义 `_(String) dgettext(...)` 等；NLS 关闭分支把
  bindtextdomain/bind_textdomain_codeset 宏化为 (String) 空操作。
  configure.ac 用 AM_GNU_GETTEXT([external])，标准 gettext 宏自带
  --disable-nls 开关。OpenWrt 构建 avahi 亦使用 --disable-nls。
- 修复（仅工作树，未 commit/push）：_configure_args() 增加 "--disable-nls"。
  autogen 仍需要 gettextize（AM_GNU_GETTEXT m4 宏），generate() 的
  gettext_datadir/ACLOCAL_PATH 逻辑保持不变。本 compat 层不依赖本地化，
  关闭后无功能损失。
- 自检：python -m py_compile 通过。等待真机预检复跑验证链接。
