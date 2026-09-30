# lcmaps-plugins-basic 1.7.1 — OHOS (aarch64/musl) 适配笔记

## 库与交付面

LCMAPS（Local Credential MAPping Service）的 basic 评测插件集：7 个
`-module -avoid-version` 动态模块（无版本号 .so），安装到 `<prefix>/lib/lcmaps/`
（moduledir，configure `--with-moduledir` 可改，默认 `${libdir}/lcmaps`）：

- `liblcmaps_dummy_bad.so` / `liblcmaps_dummy_good.so`（框架自检桩）
- `liblcmaps_ban_dn.so`（gridmapfile DN 黑名单）
- `liblcmaps_localaccount.so`（gridmapfile 本地账号映射）
- `liblcmaps_poolaccount.so`（gridmapdir 池账号映射）
- `liblcmaps_posix_enf.so`（setgroups/seteuid/initgroups 特权强制，仅运行时行为）
- `liblcmaps_ldap_enf.so`（LDAP 组映射，硬依赖 openldap）

install-data-hook 为每个模块建 `lcmaps_<mod>.mod` 符号链接（LCMAPS 框架
dlopen 的正式文件名），并安装 7 个 man8 页。

## 依赖闭包

- **lcmaps/1.6.7（without-gsi 面）**：configure 经 `AC_LCMAPS_INTERFACE([basic])`
  → `pkg-config lcmaps-basic-interface` 拿头文件面（LCMAPS_CFLAGS）。该 .pc 是
  纯头接口面，由 lcmaps/1.6.7 配方归位到 `lib/pkgconfig`（经验仓
  `build-system/lcmaps-1.6.7-pkgconfig-interface-consumption.md` 的下游消费契约：
  `requires("lcmaps/1.6.7")` + PKG_CONFIG_PATH 指向包内 `lib/pkgconfig`，无需自带
  -I 拼路径）。configure 只做头文件编译检查，不链 liblcmaps。
  **插件不链接框架**：`lcmaps_log`/`lcmaps_cred` 辅助等符号在框架 dlopen 插件时
  解析；`localaccount.c:276-278`、`poolaccount.c:461-463` 用
  `dlsym(RTLD_DEFAULT,"lcmaps_get_major_version")` 探测框架 API 版本，
  无需符号版本化。
- **openldap/2.6.7**：`configure.ac:41` 对 `ldap.h` 无开关必查
  （AC_CHECK_HEADER 硬检查），`src/Makefile.am:70`
  `liblcmaps_ldap_enf_la_LIBADD = -lldap`。头/库路径经 cpp_info 显式注入。
- **dl**：`AC_CHECK_LIB([dl],[dlopen])` 硬检查在 OHOS 工具链可过（musl dl* 在
  libc，-ldl 探针可链；知识 E013）。
- 无 OpenSSL/gsoap/voms/pam/globus 依赖（与 lcmaps/1.6.7 without-gsi 面闭包一致）。
- 不跑 autoreconf（E089：tarball 自带完整 configure/aclocal.m4）。

## 平台补丁（仅构建辅助脚本/安装规则，无源码级平台条件宏）

- `0001-config-guess-harmonyos.patch`：本 tarball 的 config.guess 为
  2014-03-23 版（比 lcmaps/1.6.7 更老，hunk 上下文不同故单独生成），不识别
  `uname -s`="HarmonyOS"，落入编译回退路径且该路径在 OHOS 存储上失败
  （同 libmnl/1.0.5、lcmaps/1.6.7 先例）。主 case 顶部加 HarmonyOS 分支。
- `0002-config-sub-ohos.patch`：config.sub（2014-07-28 版）在
  `case $maybe_os` 的 KERNEL-OS 列表与 OS 模式列表各加 `linux-ohos*`；
  实测 `aarch64-unknown-linux-ohos` 校验通过。
- `0003-configure-hmdfs-tmpdir.patch`：configure 临时目录去 umask 077 加
  chmod 755（HMDFS 上 2700 目录 owner 不可写；同 lcmaps/1.6.7、libmnl/1.0.5
  同源修法）。
- `0004-mod-install-symlink-fallback.patch`：install-data-hook 的
  `$(LN_S) → lcmaps_<mod>.mod` 在 OHOS SELinux/HMDFS 对软链接创建受限目录下
  会 Permission denied（知识 E018）。补丁保持 LN_S 优先（失败输出静默），
  失败回退 `cp -p`（copy-instead-of-link 兜底），.mod 语义（可被 dlopen）不变。

## 环境陷阱

- **E075**：C_INCLUDE_PATH 未清时 pkg-config 把 -I 过滤出 --cflags，
  LCMAPS_CFLAGS 变空 → 头文件检查失败。generate() 内对构建环境
  unset C_INCLUDE_PATH/CPLUS_INCLUDE_PATH/LIBRARY_PATH。
- **链接闭包显式化**（build-chain-pitfalls「共享库链接闭包」）：generate() 在
  toolchain 环境快照前，把全部 host 依赖 libdir 以 `-L` + `-Wl,-rpath-link`
  注入 LDFLAGS，openldap includedir 注入 CPPFLAGS；不依赖 lld 隐式 DT_NEEDED
  闭包查找与设备默认路径。
- **musl dlopen 重定位作用域实证（E004 预判命中，本 run 核心平台差异）**：
  在本设备 musl 上，`dlopen()` 的 DSO 其未定义符号**只对它自己的 DT_NEEDED
  闭包解析**——不对主程序、不对主程序的其它启动依赖库、也不对先前以
  RTLD_GLOBAL dlopen 的对象解析（最小探针三连全部复现：主程序内定义符号/
  启动 NEEDED 框架/RTLD_GLOBAL 预载，dlopen 插件均报
  `Error relocating ...: symbol not found`）。上游模型（插件携带未定义
  lcmaps_* 引用、由框架 dlopen(RTLD_NOW) 时经调用方作用域解析）在本平台
  不可重定位（CI run5/run9 实证）。**正解（POSIX 能力级适配，非平台宏）**：
  recipe 经 LDFLAGS 追加 `-llcmaps_without_gsi`，使每个插件产物携带对
  框架的显式 DT_NEEDED（框架在真实使用中必先于插件加载，NEEDED 恒可满足；
  与 PAM 模块链接 libpam 同型）。test_package 的测试二进制同型 NEEDED
  框架，并用 LD_LIBRARY_PATH 提供全部依赖 libdir。
- 插件由框架 dlopen 加载（模块允许未解析符号），产物本身无 BIND_NOW 强制
  项；框架侧 lcmaps/1.6.7 默认导出全部公共符号（nm -D 145 个 T 符号，
  SONAME liblcmaps_without_gsi.so.0），满足 dlsym(RTLD_DEFAULT)。
- **conan 包内 .pc/.la 的 prefix=/ 现象**：conan 装包走 `--prefix=/` + DESTDIR
  时，包内 .pc（lcmaps-basic-interface.pc）与 .la（libldap.la）记录
  `prefix=/`/`libdir='//lib'`。.pc 影响下游 pkg-config 消费（-I//include，
  需用上游 `--with-lcmaps-prefix` 直连）；.la 影响 libtool LIBADD 解析
  （"'//lib/liblber.la' is not a valid libtool archive"），构建前删除坏
  .la（a52dec/0.7.4 先例）。
- 无 /etc/lcmaps 硬编码路径：gridmap/gridmapdir 路径全部由调用方运行时传入。

## 上游测试（NO_UPSTREAM_TESTS，discovery.status=EVIDENCE_COMPLETE）

- 已检查入口：
  - 顶层 `Makefile.am`：SUBDIRS = doc src，仅有 stage/distsrc/distbin 自定义
    目标，无 check 目标、无 TESTS/check_PROGRAMS；
  - `src/Makefile.am`：无 check 目标；5 个 `src/*/plugin_test.c`
    （ban_dn/ldap_enf/localaccount/poolaccount/posix_enf）仅列于 EXTRA_DIST，
    是依赖手工参数的手动测试客户端，未接入任何构建目标；
  - `doc/Makefile.am`：仅 man8 页安装，非测试；
  - `configure.ac`：无 AC_CONFIG_TESTDIR/AC_PROG_CXX 测试设施。
- 证据路径（lcmaps-plugins-basic-1.7.1.tar.gz 内）：
  `Makefile.am`、`src/Makefile.am`、`doc/Makefile.am`、`configure.ac`、
  `src/{ban_dn,ldap_enf,localaccount,poolaccount,posix_enf}/plugin_test.c`。
- 结论：上游零自动化测试（无 check 目标/测试程序接入构建系统），结论
  NO_UPSTREAM_TESTS；产物验证以 test_package 的 OHOS 冒烟用例真实执行代替
  （框架 RTLD_GLOBAL 预载 → 逐个 dlopen 安装位 .mod → dlsym 三件套
  plugin_initialize/plugin_run/plugin_terminate → 包内清单核对）。

## 产物验证（权威 CI 日志 + conan 包目录实测）

- 7 个 .so 与 7 个 .mod 齐备：`<prefix>/lib/lcmaps/`（test_package 内逐一断言）。
- `llvm-readelf -d` 抽查：`liblcmaps_ldap_enf.so` 应含 `NEEDED libldap`；
  其余插件不得含 libldap/liblber。
- 框架符号供给抽查：`liblcmaps_without_gsi.so` 默认导出 lcmaps_log/
  lcmaps_get_{major,minor,patch}_version 等（test_package RTLD_NOW 链接期即验证）。
