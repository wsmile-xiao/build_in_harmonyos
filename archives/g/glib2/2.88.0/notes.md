# glib2 2.88.0 — 适配笔记

> 档案创建时间: 2026-07-17
> 状态: built

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | glib2 (GNOME glib) |
| 版本 | 2.88.0 |
| 构建系统 | meson (≥ 1.4) + ninja |
| 源码 | https://download.gnome.org/sources/glib/2.88/glib-2.88.0.tar.xz |
| sha256 | 3546251ccbb3744d4bc4eb48354540e1f6200846572bab68e3a2b7b2b64dfd07 |
| 依赖 | libffi/3.4.4, pcre2/10.45, zlib/1.3.1 |

## 二、平台适配分析（源码层）

glib 2.88 通过 meson 探测平台，关键变量 `host_system = host_machine.system()`。
OHOS 适配版 conan 的 MesonToolchain 把 `os=OHOS` 映射为 meson `host_system='harmonyos'`
（见 ci/conan/profiles/ohos-aarch64 注释）。glib 上游仅识别 linux/darwin/windows/qnx/sunos 等，
harmonyos 落到通用 unix 分支。通用分支本身可编（BSD/Solaris 都走它），但有两处必须处理：

### 1. gio-launch-desktop 链接依赖（补丁 0001，构建致命）

- `gio/gio-launch-desktop.c:205-206` 调用 `_g_fd_is_journal()`；
- `_g_fd_is_journal` 定义在 `glib/gjournal-private.c`，而该文件**仅在 `host_system=='linux'`** 时
  加入 glib_sources（`glib/meson.build:392`）与 gio-launch-desktop 源（`gio/meson.build:426`）；
- harmonyos 走通用分支时 gio-launch-desktop 仍被编译却拿不到 `_g_fd_is_journal` → 链接失败。
- gjournal-private.c 实现受 `#if defined(__linux__) && !defined(__ANDROID__)` 守卫，鸿蒙内核满足
  `__linux__`，代码是纯 POSIX（sys/socket.h、getpeername），可移植。
- **修法**：把 `host_system == 'linux'` 扩展为 `host_system in ['linux', 'harmonyos']`
  （top meson.build、glib/meson.build、gio/meson.build 全部 7 处）。鸿蒙内核兼容 Linux 接口，
  走 linux 分支正确；libmount/selinux 因配方 disable，`required: get_option(...)` 为 disabled，
  meson 不搜索、不报错。

### 2. netlink 禁用（补丁 0002，平台真理）

- `HAVE_NETLINK` 由 `<linux/netlink.h>` 头存在性决定（`meson.build:482-487`），**与 host_system 无关**；
- 鸿蒙不开放 netlink，netlink 网络监视器（`gio/gnetworkmonitornetlink.c`，含 `<linux/rtnetlink.h>`）
  不可用，且其引入的 `<linux/socket.h>` 会与 `<sys/socket.h>` 的 sockaddr_storage 冲突；
- **修法**：`if host_system != 'harmonyos' and (...)` 才设 HAVE_NETLINK。gio 据此跳过
  gnetworkmonitornetlink.c / gnetworkmonitornm.c，giomodule.c 的 `#ifdef HAVE_NETLINK` 守卫同步失效。

### 3. pcre2 发现（补丁 0003，打包兼容）

- glib 上游 `dependency('libpcre2-8', ...)`；Conan 的 pcre2 包 pkg-config 名为 `pcre2`（实测
  `conan install pcre2/10.45 -g=PkgConfigDeps` 生成 `pcre2.pc`，非 `libpcre2-8.pc`）；
- glib 找不到会回退 meson subproject（wrapdb，需联网，CI/容器无网络）；
- **修法**：找不到 libpcre2-8 时再试 `dependency('pcre2')`。pcre2/10.45 为静态库，非 Windows
  下 PCRE2_STATIC 无需定义（仅 Windows dllimport 相关），不影响。

### 4. 关闭的可选特性（配方 meson options，非补丁）

- `libmount=disabled` / `selinux=disabled`：鸿蒙工具链无；
- `nls=disabled`：避免 gettext/libintl 依赖（musl/OHOS 无）；
- `introspection=disabled` / `man-pages=disabled` / `gtk_doc=false` / `oss_fuzz=disabled`：
  鸿蒙无 gobject-introspection / rst2man / gtk-doc；
- `tests=false` / `installed_tests=false`：上游测试仅本地实测，不打包、不接 CI 门禁。

## 三、补丁文件（按 conandata 顺序累积生成，逐枚在前一枚之上 diff）

| 文件 | 说明 |
|------|------|
| 0001-add-harmonyos-host-support.patch | host_system linux 分支扩展到 harmonyos（7 处） |
| 0002-disable-netlink-for-harmonyos.patch | harmonyos 不设 HAVE_NETLINK |
| 0003-find-pcre2-via-conan-pkg-config.patch | 兼容 Conan pcre2 的 pkg-config 名（pcre2 vs libpcre2-8） |
| 0004-demote-werror-format-for-musl.patch | musl gettext 缺 format_arg，-Werror=format=2 降级 -Wformat=2 |
| 0005-build-libffi-via-subproject-fallback.patch | libffi 不在制品仓，allow_fallback 用自带子项目构建，tests=false |

> 各补丁均改 meson.build，未碰上游测试源码。累积生成确保按序 apply 不串行偏移失败。

## 四、依赖（R36）

- pcre2/10.45、zlib/1.3.1：OHOS 制品仓实测可拉，Conan 直接 requires。
- **libffi**：制品仓无（`conan list libffi/*` 返回 0）。改由 glib 自带 `subprojects/libffi.wrap`
  以 meson 子项目源码构建：conanfile.py `source()` 用 Conan HTTP（certifi，比 meson urllib 稳）
  拉取 libffi-3.5.2 源码 + wrapdb 的 meson 构建补丁，解压到 `subprojects/libffi-3.5.2/`；
  补丁 0005 让 glib `dependency('libffi', allow_fallback: true)` 走子项目离线构建（`tests=false`
  跳过 libffi testsuite 的 `add_languages(cpp)` run-check）。libffi-3.5.2 的 tramp.c 已不再依赖
  `<linux/limits.h>`（3.4.4 autotools 才有此坑）。`cpp_info.libs` 含 `ffi` 供消费者链接。
- **proxy-libintl**：glib **无条件**依赖 gettext/intl（`meson.build:2360` "We require gettext to
  always be present"，与 `nls` 选项无关），musl 无 gettext，glib 回退 `proxy-libintl` 子项目。同样
  vendor：`source()` 拉 `proxy-libintl-0.5`（github，CI 镜像）到 `subprojects/proxy-libintl-0.5/`，
  配合 `wrap_mode=nodownload` 让 `dependency('intl', allow_fallback: true)`（meson.build:2352）
  离线构建。容器内 CI 同款配置（nodownload + libffi/proxy-libintl vendored）完整构建通过。

## 四-b、CI 工具链环境坑：llvm-* 归档器名（meson 构建致命）

CI worker 导出 `AR=llvm-ar` / `AS=llvm-as` / `STRIP=llvm-strip` / `NM=llvm-nm` / `RANLIB=llvm-ranlib`，
但这些 `llvm-*` 名**不在 PATH**（hnp 只有 GNU `ar/as/strip/nm/ranlib` + `ld.lld`）。Conan MesonToolchain
把这些 env 值写进 meson native file，meson 在 configure 探测归档器时 `llvm-ar --version` →
`No such file` → `ERROR: Unknown linker(s): [['llvm-ar']]`，构建即停。

且 meson 的归档器**名字搜索解不出裸名**（连 `ar` 都报 not found），必须给**绝对路径**。
**修法（conanfile.generate）**：先 `os.environ.pop` 掉这 5 个坏 env，再用 `shutil.which` 把
真实 GNU binutils 解析成绝对路径写进 native file（`tc.ar`/`tc.as_`/`tc.strip` + `tc.binaries['nm'/'ranlib']`）；
`ld.lld` 有效保留。容器内用同样手法（shutil.which 解析 + unset env）完整构建 glib+libffi 验证通过。

## 五、本地验证与上游测试

上游测试基于 meson + gtester（TAP），测试可执行分布在 glib/tests、gobject/tests、gio/tests、
gmodule/tests、fuzzing/。上游测试总数与通过数以容器内 `meson test` 实跑为准。

**补丁 0004 的来由**：musl 的 `gettext()` 没有 glibc 的 `__attribute_format_arg`，glib 上游
`-Werror=format=2` 会把所有 `_()` 包裹的格式串判为 `-Wformat-security` 错误（glibc 因 format_arg 属性
不报）。OHOS 为 musl 系，CI 同样会触发，故把 `-Werror=format=2` 降级为 `-Wformat=2`（保留告警、不致命）。

## 六、验证记录（容器实测，2026-07-17）

构建环境：本机构建容器（aarch64 原生 musl，uname 报 Linux；hnp clang 实为 Alpine musl clang-15）。
为模拟 OHOS profile 的 `host_system='harmonyos'`，本地把 `host_system = host_machine.system()`
临时改为 `'harmonyos'`（**仅本地验证、未进配方**），使补丁 0001/0002 按 CI 同路径生效。

- 依赖：libffi 从源码静态编译（制品仓 libffi 受 acceleration policy 本地拉不到，属环境问题；
  tramp.c 需 `<linux/limits.h>`/`<linux/types.h>`，复用既有 musl linux/ UAPI shim）；
  pcre2/10.45、zlib/1.3.1 经 Conan 提供（pkg-config）。
- 工具链：real `/usr/bin/clang-15`（hnp clang wrapper 会把 `-fuse-ld=lld` 注入编译期，触发 glib 的
  `-Werror=unused-command-line-argument` size_t 探测失败——wrapper 是容器/Alpine 产物，
  真实 OHOS CI clang 无此 wrapper，故仅本地验证用 real clang-15 绕过）。
- meson setup + ninja：通过（1325 个编译目标全部完成）。

上游测试 `meson test`（提供 `/etc/machine-id`——任何 Linux/OHOS 系统都有的系统文件）：

| 类别 | 数量 |
|------|------|
| 单元测试（glib/gobject/gio/gmodule/gthread/girepository） | 287 |
| 模糊测试（fuzzing） | 30 |
| 其他（lint，需 valgrind/python） | 5 |
| **合计** | **322** |

- 通过：314（其中 gdbus-peer、gdbus-address-get-session 依赖 machine-id，提供后通过）
- 失败：1（`glib:utils-isolated` 的 `test_cleanup_handles_errors`——隔离临时目录清理在 musl 上的
  平台差异，errno ENOENT，非 glib 适配回归）
- 跳过：7（lint/portal 类，需 valgrind 或 desktop portal）

**通过率 314/322（97.5%）**。上游测试为本地实测，CI 侧未接入门禁（见 PR 正文补充说明）。

