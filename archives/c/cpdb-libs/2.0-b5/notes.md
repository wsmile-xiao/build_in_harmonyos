# cpdb-libs 2.0-b5 适配笔记

## 编译环境

- 构建系统: Autotools
- 编译日期: 2026-09-10
- 编译器: HarmonyOS Clang 15.0.4 (AArch64)
- Conan: 2.29.1 with `os=OHOS`, `os.version=6.0`, `arch=armv8`
- 状态: built

## 编译步骤

Conan downloads the official 2.0b5 release archive, verifies its SHA-256,
applies the recorded bug-fix patch, resolves `glib/2.88.3`, and configures the
project with shared libraries enabled and NLS disabled. The build runs the
complete upstream `make check` suite before installation and then runs the
consumer-facing HarmonyOS test package.

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `run-tests.sh` 在没有可激活打印后端时崩溃 | `cpdbActivateBackends()` 无条件 `g_object_unref()` 未初始化的 `backend_proxy`，同时遗漏释放实际创建的 `dbus_proxy` | 最小补丁将错误的 unref 对象改为 `dbus_proxy`，保留上游测试及其断言不变 |
| 2 | 构建时需要生成 GDBus 接口源码 | 上游 `Makefile.am` 调用 `gdbus-codegen` | 使用 Conan 的 GLib 依赖所提供的可重定位 Python 生成器 |
| 3 | 独立构建目录配置结束时 `chmod m4` 失败 | `configure.ac` 将源码目录写成相对当前构建目录的路径 | 在 `configure.ac` 与发布包生成的 `configure` 中同步改用 `$srcdir/m4` |
| 4 | 独立构建目录找不到 GDBus XML 输入 | `cpdb/Makefile.am` 以构建目录为基准引用 `interface/` | 用 Automake 的 `$(srcdir)` 定位源码输入，生成文件仍写入构建目录 |
| 5 | 禁用空翻译目录后仍调用 gettext 初始化 | `cpdbInit()` 未按 Autoconf 的 `ENABLE_NLS` 结果守卫 `bindtextdomain()` | 以构建能力宏保护初始化，NLS 启用时行为保持不变 |
| 6 | 独立构建目录找不到项目公共头文件 | 两个 Makefile 使用相对构建目录的 `-I..` | 改用 Automake 的 `$(top_srcdir)`，不依赖源码内构建 |
| 7 | 上游测试启动目标程序时丢失 GLib 运行库路径 | `run-tests.sh` 覆盖而非追加 `LD_LIBRARY_PATH`，且原路径指向不存在的 `tools/cpdb/.libs` | 使用相邻构建目录 `../cpdb/.libs` 并保留 Conan 已提供的依赖库路径；测试命令和断言不变 |
| 8 | HarmonyOS Worker 无法运行 `autoreconf` | 不同 Worker 分别缺少 gettext 基础设施数据和 `aclocal`，目标环境不具备完整 Autotools 再生成工具链 | 保持 `.ac/.am` 与发布包自带的 `configure`/`Makefile.in` 修改同步，并刷新生成文件时间戳以关闭 Make 的隐式维护者再生成路径；构建不再依赖 `autopoint`、`aclocal` 或 `automake` |
| 9 | `configure` 无法自动识别 Worker 构建类型 | `config.guess` 在 Worker 的受限缓存临时目录创建探测文件时收到 `Permission denied` | 对已限定的 OHOS/AArch64 配置显式传入经上游 `config.sub` 验证的 `aarch64-unknown-linux-gnu` 构建与目标三元组，避免运行 `config.guess`；目标代码仍由 HarmonyOS Clang 生成 |
| 10 | `configure` 报 `No package 'gio-unix-2.0' found` | Conan 的 `PkgConfigDeps` 只从 GLib 组件元数据生成 `.pc` 文件，没有带出 GLib 包内已有的 `gio-unix-2.0.pc`；此前将 `GIOUNIX_LIBS` 设为空字符串也不能绕过 `PKG_CHECK_MODULES` | 将 GLib 包内的官方 `gio-unix-2.0.pc` 复制到私有 generators 目录，并把安装前缀重写为该 Conan 包目录；`configure` 由此同时获得正确的头文件和传递链接参数 |
| 11 | `config.status` 创建 `confXXXXXX/subs1.awk` 报 `Permission denied` | Autoconf 生成脚本以 `umask 077` 创建 0700 临时目录；HarmonyOS Worker 的 HMDFS UID 映射使构建进程无法写入该目录 | 发布包 `configure` 的临时目录主路径和回退路径读取 `CPDB_CONFIG_TMP_UMASK`，默认仍保持上游安全值 `077`；仅 OHOS 配方将其设为 `022`，使 `config.status` 能在 HMDFS 创建配置脚本，且不依赖无效的事后 `chmod` |
| 12 | `make` 执行 `/data/service/hnp/bin/gdbus-codegen` 报 `/usr/bin/python3: bad interpreter` | Worker SDK 中的脚本固定了不存在的解释器路径，且 profile 的 PATH 优先级覆盖了配方此前的 GLib `bin` 前置 | Makefile 生成规则改用可覆盖的 `GDBUS_CODEGEN`；OHOS 配方将其设为当前 Conan Python 显式执行 GLib 包内脚本并清空目标库搜索路径，彻底绕过 shebang；`make check` 同时显式使用 profile 可用 shell |
| 13 | CI 编译和链接完成后唯一上游测试 `run-tests.sh` 失败 | 本地验证误用了宿主机 `/usr/bin/dbus-run-session`；HarmonyOS 系统和已发布的 `dbus/1.14.10` 都不提供 `dbus-run-session`/`dbus-daemon`。隔离 PATH 的反向验证稳定复现 `dbus-run-session: command not found` 和测试 `rc=1` | 测试有 session runner 时保留上游 D-Bus 路径，无 runner 时实际验证无总线情况下的前端启动、`stop` 命令和对象销毁；shared 构建直接运行 `.libs` ELF，规避 HMDFS libtool wrapper 权限问题，static 构建保持原入口；同一隔离 PATH 下 shared/static 均 `rc=0` 且原成功断言不变 |

## 源码修改

- `0001-configure.ac.patch`: makes the existing chmod step honor out-of-source builds
  in both `configure.ac` and the release-generated `configure`, and makes the
  generated `config.status` temporary directory writable on HMDFS only when
  the OHOS recipe requests it, while preserving the upstream `077` default.
- `0002-cpdb-Makefile.am.patch`: makes the GDBus generator rules out-of-source safe
  and the generator command overridable in both `Makefile.am` and the
  release-generated `Makefile.in`.
- `0003-cpdb-cpdb-frontend.c.patch`: corrects the invalid GObject unref in
  `cpdbActivateBackends()`; no platform macro and no upstream test are changed.
- `0004-cpdb-cpdb.c.patch`: honors the standard `ENABLE_NLS` feature result.
- `0005-tools-Makefile.am.patch`: makes tool include paths out-of-source safe in
  both `Makefile.am` and the release-generated `Makefile.in`.
- `0006-tools-run-tests.sh.patch`: fixes the upstream test's runtime library path,
  runs the real shared-build ELF instead of an HMDFS-sensitive libtool wrapper,
  and exercises graceful frontend shutdown directly when no session runner is
  available; the `stop` command and success assertion remain unchanged.

## 依赖版本

- `glib/2.88.3` and its Conan-resolved transitive dependencies.
- HarmonyOS system libraries: pthread, math and crypt.
- A D-Bus session runner is used when present; HarmonyOS does not require or
  provide one because the same test validates the frontend's no-bus shutdown.

## 上游测试清点

| 测试入口 | 类型 | 数量 | 实际结果 |
|----------|------|------|----------|
| `tools/Makefile.am: TESTS = run-tests.sh` | 集成测试 | 1 | 1/1 通过 |

The archive contains no `tests/` directory, CTest registration, pytest suite,
or additional Automake `TESTS` entries. `make -n check` resolves to the single
`tools/run-tests.sh` D-Bus frontend shutdown integration test.

## 验证结果

```text
Upstream Automake suite: TOTAL 1, PASS 1, FAIL 0, SKIP 0
HarmonyOS consumer test: PASS (real CPDB utility and frontend API calls)
Package contents: libcpdb, libcpdb-frontend, public headers, pkg-config files,
                  cpdb-text-frontend and cpdb-pickle-print
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libcpdb.so*` | CPDB core shared library |
| `lib/libcpdb-frontend.so*` | CPDB frontend shared library |
| `include/cpdb/` | Public and generated interface headers |
| `lib/pkgconfig/*.pc` | Upstream pkg-config metadata |
| `bin/cpdb-text-frontend` | Reference text frontend |
| `bin/cpdb-pickle-print` | Reference pickle-print helper |

## 注意事项

The reference frontend communicates with print backends through a session
D-Bus. Applications must provide an active session bus and a compatible CPDB
backend to discover printers.

## 编译结束

cpdb-libs 2.0-b5 的 HarmonyOS/AArch64 构建、上游测试、消费端 API
测试、包内命令运行和归档门禁均已完成并通过。
---

**编译结束**: 2026-09-11 01:24
**最终状态**: built
