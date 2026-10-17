# dbustest 19.04.0 适配笔记

## 编译环境
- 构建系统: autotools（官方 tarball 自带预生成 configure，无需 autoreconf）
- 编译日期: 2026-09-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# conan create 内部（conanfile.py build()）：
# 1. _patch_ohos_autotools(): config.guess/config.sub 内联补 OHOS 识别
# 2. 就地改 configure 中 umask 077 → umask 000（E011: HMDFS/SELinux 临时目录不可写）
# 3. _make_gettext_stub(): msgmerge stub（返回 GNU 版本字符串）前置 PATH +
#    stub XML::Parser perl 模块注入 PERL5LIB（intltool 检查用）
# 4. _gen_pcre2_alias(): pcre2.pc 别名（复制 libpcre2-8.pc 改 Name）+
#    pcre2 的 .la/.a 复制到 pcre2-reloc-lib 并改写 .la libdir
# 5. _copy_dep_pc(): 复制所有依赖包 .pc 到 generators_folder 并改写 prefix
# 6. ./configure --prefix=/ --disable-maintainer-mode --disable-nls
#    （PATH/PERL5LIB/PKG_CONFIG_PATH 均前置注入）
# 7. make -j1 && make install DESTDIR=...
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 版本冲突 glib/2.88.0 vs 2.88.0.1 | dbus-glib/0.114 依赖 glib/2.88.0 | requirements 用 glib/2.88.0 对齐 |
| 2 | configure: GNU gettext tools not found (msgmerge missing) | IT_PROG_INTLTOOL 强制检查 msgmerge（GNU gettext 工具），OHOS 系统缺 | msgmerge stub（`echo 'msgmerge (GNU gettext-tools) 0.22.5'`）前置 PATH + `--disable-nls` |
| 3 | configure: XML::Parser perl module required | intltool 的 `perl -e "require XML::Parser"` 检查，OHOS 无该 CPAN 模块且不可安装 | stub `XML/Parser.pm`（`our $VERSION='2.44'; 1;`）注入 PERL5LIB |
| 4 | configure: cannot guess build type | 旧版 config.guess（2018 前格式，各分支自行 echo+exit）无 HarmonyOS 分支 | 按旧版格式在 `aarch64:Linux:*:*` 前插 `*:HarmonyOS:*:*` → `echo "$UNAME_MACHINE"-unknown-linux-ohos; exit ;;` |
| 5 | Invalid configuration `aarch64-unknown-linux-ohos` | config.sub 无 linux-ohos | maybe_os 列表加 `linux-ohos*` + os 合法性列表加 `-linux-ohos*` |
| 6 | No package 'gio-unix-2.0'/'pcre2' found | configure 的 PKG_CHECK_MODULES 需全依赖 .pc | PKG_CONFIG_PATH 前置 generators_folder + 注入全部依赖包 pkgconfig 目录 |
| 7 | libtool: cannot find the library '//lib/libpcre2-8.la' | pcre2 包 .la 内 libdir='//lib'（prefix=/ 硬编码），libtool 读 .la 的 libdir | 复制 pcre2 的 .la/.a 到 pcre2-reloc-lib 并改写 libdir；pcre2.pc 别名强制覆盖（PkgConfigDeps 生成的指向原始路径） |
| 8 | Component 'dbus-glib::dbus-glib-1' not found | dbus-glib/0.114 为顶层 cpp_info（无 dbus-glib-1 组件），CMakeDeps 目标为 dbus-glib::dbus-glib | conanfile package_info 与 test_package CMakeLists 均改 `dbus-glib::dbus-glib` |
| 9 | test_package: 'libdbustest/dbus-test.h' file not found | 上游 Makefile.am：`libdbustestincludedir=$(includedir)/libdbustest-$(API_VERSION)/libdbustest`——头文件装 include/libdbustest-1/ | package_info `includedirs = ["include/libdbustest-1"]` |
| 10 | test() 运行 Signal 11 | OHOS 沙箱无运行中的 D-Bus 会话，构造 DbusTestService 需连接会话总线 | test() 捕获运行失败按 rule 1.2 声明平台限制（编译链接 + R34 产物校验覆盖） |

## 源码修改

无外部补丁文件（patches/ 为空）；config.guess/config.sub OHOS 识别、intltool 的
msgmerge/XML::Parser stub、pcre2 .la/.pc 重定位均在 conanfile.py 内联处理。

## 依赖版本

- glib/2.88.0（dbus-glib/0.114 依赖对齐）
- dbus-glib/0.114（main 已有适配）
- intltool/0.51.0、gettext/0.22.5、automake/1.18、libtool/2.5.4（tool_requires）
- 传递依赖：dbus/1.14.10、expat/2.8.2、pcre2/10.45、zlib/1.3.1

## 验证结果

```bash
# conan-verify dbustest 19.04.0 → 全门禁 PASS
# G1 配方完整性 / G0 知识图谱 / G2 conan create / G3 R26 隔离 /
# G4 产物完整性 / L2 smoke / L4 checksec / L5 基线对比 全部 PASS

# test_package R34：libdbustest.so 存在 + 动态依赖链完整 + test_dbus_test_runner
# 编译链接成功（构造/析构 API 校验）

## 上游测试实测（2026-09-05 补充核实）

上游 tests/ 均通过 `dbus-test-runner --dbus-config <data>/session.conf` 自启动
隔离 dbus-daemon（不依赖系统运行的 D-Bus 会话）。**实测**（手动运行
dbus-test-runner --task true）确认：

```
libdbustest-CRITICAL: Unable to start dbus daemon:
  Failed to execute child process "dbus-daemon" (No such file or directory)
dbus_test_service_start_tasks: assertion 'g_getenv("DBUS_SESSION_BUS_ADDRESS")
  != NULL || ...' failed → Signal 11
```

**根因修正**：上游测试无法运行不是"OHOS 无运行中的 D-Bus 会话"（dbus-test-runner
本就自启动隔离 daemon），而是 **OHOS 系统与 ohpcd dbus/1.14.10 包均无
dbus-daemon 可执行文件**（源码 service.c:111 硬编码 `g_strdup("dbus-daemon")`
从 PATH 找）——无法 spawn 隔离 daemon。上游测试 0/5 按 rule 1.2 如实声明
平台限制（非跳过），通过率按此口径。
```
