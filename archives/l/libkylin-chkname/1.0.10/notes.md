# libkylin-chkname 1.0.10 适配笔记

## 软件与源码

- 上游：openKylin `libkylin-chkname`，提供 `kylin_username_check` 与
  `kylin_username_strerror` 两个 C API；公开头已提供 `extern "C"`，可直接供
  C++ 消费者使用。
- 官方发布包：`libkylin-chkname_1.0.10.orig.tar.gz`，SHA-256 为
  `3c09c7727c902886b1650efed27ac6b315040a6edf2bc45c738b39d9bbceb94f`。
- 许可证：MulanPSL-2.0。产物是纯库、头文件、保留名数据与翻译目录，不提供命令，
  因而不需要 `commands.json`。

## 适配要点

1. 官方包只带 `configure.ac`/`Makefile.am`，构建前由宿主的 Autotools 和 gettext
   生成构建系统，实际编译与链接仍完全使用 Conan OHOS profile 的 Clang。
2. `0001` 显式指定 `build-aux` 和 `m4`，避免 libtoolize 因父目录残留
   `install-sh` 而把 `ltmain.sh` 写到源码树外。
3. `0002` 按上游数据布局安装 `reserved-names`，并为保留名与 locale 路径提供环境
   覆盖；Conan `runenv_info` 指向包内 `share`，默认系统路径仍保持兼容。
4. 目标运行时依赖 `gettext/0.22.5.1` 的 libintl；该版本的 OHOS/armv8 recipe 与
   二进制在适配前已分别完成下载和 `--build=never` 安装验证。
5. 补丁不使用 `__OHOS__` 条件编译，所有可移植修复对 Linux/OHOS 共用。
6. `automake/1.18` 生成的 `config.sub` 已接受
   `aarch64-unknown-linux-ohos`，但 `config.guess` 不能从真机的
   `uname -s=HarmonyOS` 推导该三元组。配方在 `autoreconf` 后补入原生平台识别，
   不使用会跳过运行时能力探测的 `--build/--host` 绕行参数。
7. `0003` 将 `-lintl` 只关联到实际库目标，并以 Libtool `-no-undefined` 强制共享库
   解析该依赖、写入 `DT_NEEDED libintl.so.8`。不能直接使用探测结果 `$(LIBINTL)`：
   OHOS 上的 Libtool 会将其中的绝对 `.so` 路径降为 `-L` 后省略库本身。配方不把
   `-lintl` 写入全局 `LIBS`，因此 `AC_PROG_CC` 的最早运行探针保持无外部依赖，
   避免不同 HarmonyOS Worker 的动态加载路径造成 `configure` 错误 77。
8. HarmonyOS Worker 的源码与构建目录位于 HMDFS；其 UID 映射会使 Autoconf
   通过 `umask 077` 创建的 `confXXXXXX` 目录无法由当前进程写入，表现为
   `config.status` 创建 `subs1.awk` 时 `Permission denied`。配方按知识库 E011
   在 `autoreconf` 后、`configure` 前仅为 OHOS 构建将生成脚本中的掩码改为
   `022`，Linux 构建仍保留上游默认值。
9. Worker 默认 PATH 只暴露 `msgfmt`/`xgettext`，而 `msgmerge` 位于
   `/data/service/hnp/gettext.org/gettext_0.26/bin`。缺失时 configure 将其替换为
   `:`，但 PO 规则随后仍要求它生成 `*.1po`，最终令 `msgfmt` 找不到输入。
   配方从已验证的宿主 `autopoint` 推导同源工具目录并显式设置 `MSGMERGE`；翻译
   目录继续完整构建和安装，不跳过 NLS 内容。
10. Worker 的共享 `/storage/Users/currentUser/usr/local/include` 可能先于依赖包
    include 路径，并提供把 gettext API 重定向为 `g_libintl_*` 的 GLib proxy
    `libintl.h`；但 `gettext/0.22.5.1` 的 `libintl.so.8` 导出标准
    `libintl_*`，造成头库 ABI 错配。配方将同一个 Conan gettext 包的 include
    与 lib 搜索路径同时前置，确保编译、Autoconf 探测和最终链接使用同一实现。
11. `gettext/0.22.5.1` 的 `package_type=application` 不向 CMake 消费者传播库名；
    配方在自身消费者元数据中只补充直接 ABI 依赖 `intl`。共享产物通过
    `DT_NEEDED` 解析它，静态产物也会在消费者链接行中得到所需的 `-lintl`。

## 测试审计与覆盖

上游 1.0.10 发布包没有 `test/`、`tests/`、测试源文件或脚本；`configure.ac`
没有 Autotest 入口，`Makefile.am` 也没有 `TESTS`/`check_PROGRAMS`。因此上游实测
统计为 0 项，并在 `test_package/MANIFEST.yml` 保留完整静态审计证据。

`test_package` 是真实 C++ 包消费者，链接安装后的库并执行 20 项用例：合法名称、
空值/长度/字符规则、十进制/十六进制/八进制拒绝、保留名开关及缺失资源错误、
错误文本，以及 HarmonyOS AArch64 目标宏和包内数据/locale 的专项验证。
---

**编译结束**: 2026-09-14 12:14
**最终状态**: built
