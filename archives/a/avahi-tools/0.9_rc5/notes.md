# avahi-tools 0.9_rc5 适配笔记

## 概述

- **软件**：avahi-tools（Avahi 客户端命令行工具集，取自 avahi 源码树 `avahi-utils/` 子目录）
- **版本**：0.9_rc5（上游 tag `v0.9-rc5`，PACKAGE_VERSION "0.9-rc5"）
- **官方源**：https://github.com/avahi/avahi/archive/refs/tags/v0.9-rc5.tar.gz
- **sha256**：`5b0a9d88110b0fc8aaafc5cc0a26e83e7d2a4aca3a36bc27c9b626db7ead27b0`
  （本机实测下载校验一致；与已合入的 avahi-glib / avahi-compat-libdns_sd 同一归档）
- **许可证**：LGPL-2.1-or-later
- **构建系统**：Autotools（归档不含生成的 configure，需 autogen.sh 引导）
- **包类型**：application（产出 4 个可执行文件 + 上游 install-exec-local 的 5 个别名）

## 上游结构调查

- `avahi-utils/Makefile.am`：`HAVE_DBUS` 条件下声明
  `bin_PROGRAMS = avahi-browse avahi-resolve avahi-publish avahi-set-host-name`，
  各程序链接 `../avahi-client/libavahi-client.la` 与 `../avahi-common/libavahi-common.la`；
  `HAVE_GDBM` 下才编译 `stdb.c`（--dump-db 服务类型库特性）。
  `install-exec-local` 创建 5 个符号链接别名（先 `rm -f` 再 `$(LN_S)`，与 HMFS
  "不能 ln -sf 覆盖" 约束天然兼容）。
  **该 Makefile.am 未定义任何 TESTS。**
- configure.ac：`BUILD_CLIENT` 仅要求 `HAVE_DBUS`；`Building avahi-utils: ${BUILD_CLIENT}`
  ——即 utils 与 client 绑定，dbus 是唯一硬依赖。`--enable-tests` 默认 no。
- 测试分布审计（TESTS 关键字全树扫描）：
  - `avahi-common/Makefile.am`：TESTS 注册 7 个离线单元测试
    （strlst/domain/alternative/timeval/watch/watch-thread/utf8），全部为纯输入/
    编码类断言，逐一核查源码确认**不引用任何 AvahiClient 符号、不需要守护进程**；
  - `avahi-client/Makefile.am`：ENABLE_TESTS 下只构建 5 个 noinst 程序
    （client-test/srv-test/xdg-config-test/rr-test/check-nss-test），**未注册 TESTS**，
    且语义上需要运行中的 avahi-daemon 与 D-Bus system bus；
  - 其余带测试的子目录（avahi-core/daemon/compat-howl/libevent/glib/examples/tests）
    不在本拆包构建范围。

## W0 依赖核验

复用同源兄弟包已验证的发布版本（均已在制品仓发布并被消费）：

- dbus/1.14.10（libavahi-client 链接 D-Bus）
- expat/2.8.2.1 override（规避 conancenter expat/2.8.2 传递 tool_require
  cmake/4.4.2 在 OHOS 的 KeyError 'OHOS'，avahi-compat-libdns_sd R17 同款）
- 工具链：automake/1.18、libtool/2.5.4、gettext/0.22.5.1（autoconf/m4 由 SDK 提供）

## 构建策略（继承同源兄弟包的全部真机踩坑修复）

本配方以 avahi-compat-libdns_sd 的配方为骨架（相同的 common→client 依赖序）、
叠加 avahi-glib 的 E337 启动器闭包，逐项对应真机预检历史修复：

1. **bootstrap（R18）**：`NOCONFIGURE=1 CONFIG_SHELL=$SHELL $SHELL autogen.sh`，
   全程不硬编码 bash；configure 亦经 sh 显式执行。
2. **E337 启动器闭包**：aclocal/automake 用 perl ELF 启动器（HMFS 拒绝直接执行跨 UID
   Conan 缓存脚本）；libtoolize 用 sh ELF 启动器并把 prefix/datadir/pkgauxdir/
   pkgltdldir/aclocaldir 重定位到包目录；gettextize 保持脚本形态（autogen.sh 用
   `sed ... $(which gettextize) | sh -s --` 把它当 shell 文本读入，ELF 启动器会破坏该
   用法——E337 forbid_2 明确记录的例外），仅重定位 prefix 并保证 PATH 可发现。
3. **gettext 数据路径（R19）**：注入 `gettext_datadir=<gettext 包>/share/gettext` 与
   `ACLOCAL_PATH=<gettext 包>/share/aclocal`，绕开 gettextize 硬编码的构建机绝对路径。
4. **dbus pkg-config shim**：dbus 包不带 dbus-1.pc，generate() 从包目录生成并前置
   PKG_CONFIG_PATH。
5. **CC/CXX 显式化**：从 profile 的 tools.build:compiler_executables 取，避免选中
   HMFS 的 cc 包装器。
6. **AS_TMPDIR（R22/R23，E011/E112/E118）**：autogen 生成 configure 后、运行前文本
   移除 `um(?:ask|ash) 077 && mktemp -d|mkdir` 前缀（覆盖 heredoc 内 config.status
   模板），避免 2700+setgid 临时目录被 HMFS 拒写。
7. **configure 开关（R20/R21/R25）**：`--with-xml=none`（跳过 expat/bsdxml 强制探测）、
   `--disable-libsystemd --with-systemdsystemunitdir=no`（OHOS 无 systemd）、
   `--disable-nls`（消除 libavahi-common 静态库的 g_libintl_* 未定义符号）。
8. **串行构建**：`make -C avahi-common → avahi-client → avahi-utils`，-j1。

## 打包策略（应用包不跑 make install）

- HMBS install shim 只接受单文件两参调用、且 HMFS 符号链接/chmod 能力受限；
  应用包按 abbtr/git-who 先例**手动收集产物**：
  - 按 ELF 魔数从 `avahi-utils/.libs/<name>`（或顶层，兼容两种 libtool 布局）挑出
    真实二进制复制到 `<pkg>/bin/`，杜绝把 libtool wrapper 脚本当产物打包；
  - 复刻 install-exec-local 的 5 个别名：先 `rm -f` 再 `os.symlink`，OSError 时退化为
    独立副本（功能等价，argv0 语义差异仅在多别名显示名）；
  - 附 LICENSE。
- `cpp_info.libs = []`、`cpp_info.bindirs = ["bin"]`；软件级目录含 commands.json（R38）。

## 上游测试接入

- 命令：`make -C avahi-common check`（automake TESTS，预期 discovered=7，数字以真机
  输出为准）；build() 解析 `^PASS:/^FAIL:/^SKIP:` 输出 HMBS_UPSTREAM_TEST_RESULT 标记，
  discovered=0 或存在 FAIL 即失败（防"空跑也 PASS"的假阴性）。
- test_package：`test_avahi_tools.sh` 对 4 个工具执行 10 条真实断言（每工具
  --help/--version 共 8 条 + 非法选项/缺参失败路径 2 条），计数写入结果文件，
  conanfile 读取后输出唯一 HMBS_TEST_PACKAGE_RESULT 标记。
- 断言依据（上游源码核实）：四个工具 help() 均含 `-h --help` 字样；COMMAND_VERSION
  分支打印 `%s PACKAGE_VERSION`（"0.9-rc5"）；getopt_long default 分支返回 -1 使
  parse_command_line 失败 → exit 1；set-host-name 无参时 "Invalid number of arguments"
  → exit 1。浏览/发布等实际功能依赖 D-Bus system bus 上的 avahi-daemon，属运行环境
  约束，不在消费者测试范围。

## 与兄弟包的差异点

- 无 glib/gobject，故无 GLIB20_CFLAGS/GLib Python 代码生成器相关处理；
- 无 .so/.a 产物需要 cpp_info.libs（应用包），也就没有静态库消费方的链接顺序问题；
- 不跑 make install，install shim（R24）整类问题不适用。

## 已知限制

- HarmonyOS PC 默认无 D-Bus system bus 上的 avahi-daemon，工具的实际浏览/发布功能
  无法端到端演示；这是运行环境约束而非适配缺陷，CLI 离线路径（help/version/参数
  校验）完整可用。
- 别名在 HMFS 不支持 symlink 时退化为独立副本，与上游符号链接语义略有差异
  （仅影响 argv0 显示的程序名）。

## 自检记录（本机静态验证）

- python -m py_compile 通过（conanfile.py 与 test_package/conanfile.py）；
- conandata.yml/manifest.yaml/MANIFEST.yml yaml.safe_load 解析通过，
  sha256 与官方归档一致（本机下载实测）；
- test_avahi_tools.sh 经 busybox ash/dash 语法检查通过；
- 全部文件 UTF-8 无 BOM、LF 行尾；无未完成事项的占位标记。
