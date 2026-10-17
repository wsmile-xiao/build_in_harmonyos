# kea-hook-lease-query 3.0.3 适配笔记（HarmonyOS PC / OHOS aarch64）

目标：ISC Kea 3.0.3 的 lease-query（bulk lease query）hook 插件
`libdhcp_lease_query.so`（源码路径 `src/hooks/dhcp/lease_query/`）。

## 编译环境

- 构建系统：Meson（Kea 3.0 起由 Autotools 迁移到 Meson）
- 编译日期：2026-09-20
- 编译器：clang/clang++ 15.0.4（`/data/service/hnp/bin`），triplet `aarch64-linux-ohos`
- Conan profile：`ci/conan/profiles/ohos-aarch64`（host = build = OHOS armv8，native 构建）
- 状态：built

## 编译步骤

```bash
# 1. 源码：官方发布包 ftp.isc.org
curl -o kea-3.0.3.tar.xz https://ftp.isc.org/isc/kea/3.0.3/kea-3.0.3.tar.xz
# sha256 = 09702ddb078b637e85de9236cbedd3fb9d7af7c6e797026c538b45748ad4d631

# 2. Conan 依赖 + Meson 工具链（配方内 generate() 完成）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#    → conan_meson_native.ini（compiler/binaries/pkg_config_path/buildtype）

# 3. 配置 / 编译 / 测试
meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled \
    -Dcrypto=openssl -Dmysql=disabled -Dpostgresql=disabled -Dnetconf=disabled -Dkrb5=disabled
meson compile -C <builddir>
meson test -v -C <builddir> dhcp-lease-query-tests dhcp-lease-query-libloadtests
```

## 遇到的问题与解决方案

| # | 问题（首个错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]` | Conan 把 buildenv `AR=llvm-ar` 原样写进 machine file；CI/本机 PATH 不保证含 llvm-ar/llvm-ranlib，meson `project()` 探测静态链接器失败 | `generate()` 里从 `tools.build:compiler_executables` 的编译器绝对路径推导同目录 `llvm-ar`/`llvm-ranlib` 写入 `tc.binaries`（与 c-list 1.1.0 先例一致） |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | `platform.system()` 在 OHOS 返回 `HarmonyOS`，meson 据此报告 host system=`harmonyos`；Kea 用 `build_machine.system()` 做平台分支，白名单里没有 harmonyos | 补丁 0001：顶层 `meson.build` 把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`（一处修改，所有子目录分支随之走 Linux 路径） |
| 3 | `chaos: Boost TLS support broken.`（`HAVE_GENERIC_TLS_METHOD` DID NOT COMPILE） | OHOS musl `pthread.h` 未声明 `pthread_setcancelstate`，而 `boost/core/detail/sp_thread_sleep.hpp` 无条件调用（Boost.Asio 链路必经） | `tc.extra_cxxflags` 注入 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（boost 官方逃生宏，1.83+ 提供） |
| 4 | `cpp.run()` 探针 `LOG4CPLUS_INITIALIZER_H … NO (127)` / `meson.build:824:24: ERROR: Unknown variable "log4cplus"` | Meson 的特性探针是 compile-and-run，native 构建下会真实执行；host 共享依赖 `liblog4cplus.so.9` 不在配置期运行环境里（127 = 加载失败） | `generate()` 用 `Environment` 把各 host 依赖的 `libdir` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")`（build 阶段自动 source） |
| 5 | `src/lib/dhcp/iface_mgr_linux.cc:40: error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 `linux/socket.h`（bionic 派生，含 `struct sockaddr_storage`）与 musl `sys/socket.h` 的同名结构冲突；`linux/rtnetlink.h` 会间接包含前者 | 补丁 0002：包含 netlink 头前用 `#define sockaddr_storage __linux_uapi_sockaddr_storage`（`__linux__ && !__GLIBC__` 守卫），include 后 `#undef`，保留 libc 侧定义 |
| 6 | 制品仓 boost 版本约束 | `boost/1.90.x` 缺 `boost/interprocess/sync/interprocess_upgradable_mutex.hpp`（meson 14 项强制头之一），`1.91.x` 缺 `circular_buffer/format/assign`；且制品仓 boost 包不含 `libboost_system` | 固定 `boost/1.85.0`（不得用版本范围），并要求 `meson >= 1.10`（boost 模块 header-only 回退） |

## 源码修改

`patches/0001-meson.build.patch`

```meson
 SYSTEM = build_machine.system()
+# OpenHarmony/HarmonyOS shares the Linux userspace ABI (musl libc, Linux
+# syscalls, linux iface_mgr/pkt_filter back-ends). Meson reports the
+# platform as 'harmonyos'; normalize it to the Linux branch below.
+if SYSTEM == 'harmonyos'
+    SYSTEM = 'linux'
+endif
 if SYSTEM == 'linux'
```

`patches/0002-src-lib-dhcp-iface_mgr_linux.cc.patch`

```c
 #include <net/if.h>
+#if defined(__linux__) && !defined(__GLIBC__)
+#  define sockaddr_storage __linux_uapi_sockaddr_storage
+#  define KEA_RESTORE_SOCKADDR_STORAGE 1
+#endif
 #include <linux/rtnetlink.h>
+#ifdef KEA_RESTORE_SOCKADDR_STORAGE
+#  undef sockaddr_storage
+#  undef KEA_RESTORE_SOCKADDR_STORAGE
+#endif
```

两个补丁均不含 `__OHOS__` 平台宏（补丁 0002 用标准 libc 鉴别宏
`__linux__ && !__GLIBC__`，对任何 musl + Linux UAPI 组合都成立）。

## 依赖版本

| 依赖 | 版本 | 类型 | 制品仓验证 |
|------|------|------|-----------|
| boost | 1.85.0 | 强制（头文件全集 + `modules:['system']`） | `conan download` exit 0 |
| log4cplus | 2.2.0.1 | 强制（日志后端） | `conan download` exit 0 |
| openssl | 3.5.8.1 | 强制（默认 crypto 后端） | `conan download` exit 0 |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） | `conan download` exit 0 |
| zlib | 1.3.1 | 传递（boost 配方 requires） | `conan download` exit 0 |
| meson | 1.11.0 | 构建工具 tool_requires | `conan download` exit 0 |
| ninja | 1.13.1 | 构建工具（系统提供） | 系统 |
| libpq | 18.6 | 可选（仅 `-o with_postgresql=True` 时引入） | `conan install` exit 0 |

可选后端中，MySQL 侧无法启用：制品仓 `mysql/8.0.46`、`percona-server/8.4.10_10`、
`mariadb/11.8.8` 均只发布客户端工具与静态客户端库，不含可运行的 `mysqld`/`mariadbd`；
且 `mysql-client/8.4.11` 固定 `openssl/3.5.6`，与本配方的 `openssl/3.5.8.1` 冲突。
PostgreSQL 侧通过 `libpq/18.6` 打通：配方选项 `with_postgresql`（默认 `False`）开启后
meson `-Dpostgresql=enabled`，56 个 PgSQL 后端用例注册并全部通过。其余可选后端
（botan/krb5/netconf）制品仓无可消费依赖，继续显式 `disabled`。

## 验证结果

```bash
$ ninja -j6 src/hooks/dhcp/lease_query/libdhcp_lease_query.so \
      src/hooks/dhcp/lease_query/tests/dhcp-lease-query-tests \
      src/hooks/dhcp/lease_query/libloadtests/dhcp-lease-query-libload-tests
exit_code=0                                         # 282/282 目标

$ ./dhcp-lease-query-tests --gtest_color=no
[==========] 153 tests from 19 test suites ran. (1597 ms total)
[  PASSED  ] 153 tests.
exit_code=0

$ ./dhcp-lease-query-libload-tests --gtest_color=no
[==========] 7 tests from 1 test suite ran. (137 ms total)
[  PASSED  ] 7 tests.
exit_code=0
```

```bash
# 包内测试（test_package，2 项：消费者契约 + 鸿蒙特有）
$ conan test test_package kea-hook-lease-query/3.0.3 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>
# (1) 消费者契约
$ ./test_lease_query_hook <pkg>/lib/kea/hooks/libdhcp_lease_query.so
libdhcp_lease_query.so loaded (hooks version 30003)
kea-hook-lease-query/3.0.3 OK
# (2) 鸿蒙特有平台校验（本机 OHOS aarch64 实测输出）
$ ./test_ohos_platform <pkg>/lib/kea/hooks/libdhcp_lease_query.so
ok   - ELF magic present
ok   - ELFCLASS64 (64-bit OHOS PC target)
ok   - e_machine == EM_AARCH64 (OHOS aarch64)
ok   - PT_DYNAMIC segment present
info - DT_NEEDED closure (13 entries)
info -   libkea-dhcpsrv.so.131
info -   libkea-process.so.91
info -   libkea-stats.so.53
info -   libkea-tcp.so.33
info -   libkea-dhcp.so.109
info -   libkea-hooks.so.121
info -   libkea-cc.so.83
info -   libkea-asiolink.so.88
info -   libkea-log.so.75
info -   libkea-util.so.102
info -   libkea-exceptions.so.45
info -   libc++_shared.so
info -   libc.so
ok   - DT_NEEDED links the OHOS musl libc ("libc.so")
ok   - DT_NEEDED does not use the glibc naming ("libc.so.6")
ok   - DT_NEEDED links the OHOS libc++ runtime ("libc++_shared.so")
ok   - OHOS loader dlopen(RTLD_NOW) resolves the plug-in
kea-hook-lease-query/3.0.3 OHOS platform check OK
exit_code=0
```

- 上游测试用例总数：源码 `TEST/TEST_F` 宏 265（tests）+ 7（libloadtests）
- 默认配置实际注册并执行：153 + 7 = 160，通过 160，失败 0，跳过 0
  （2026-09-20 本机复验：meson test Ok 2 / Fail 0，153+7 全 PASSED，日志
  `~/tmp/kea-lq-logs/conan-create-r4.log`）
- 开启 PG 后端（`-o with_postgresql=True`）构建验证：1478 个 ninja 目标全部编译
  链接成功，56 个 PgSQL 条件块用例随 `-Dpostgresql=enabled` 注册（209 + 7 = 216）；
  历史实测记录（2026-09-17，当时本机有 PostgreSQL 18.3 服务）：216/216 全通过，
  0 失败 0 跳过。2026-09-20 复验环境无 PostgreSQL 服务端（`psql`/`postgres` 二进制
  均不存在，cmd-pkgs 亦无），PgSQL* 套件 SetUp 阶段 `runPgSQLSchema failed` 即中止
  （SIGABRT）——该组用例需真实数据库服务，属环境限制非适配缺陷；默认配置（交付形态）
  的 160 例在本环境全绿。MySQL 侧仍无法启用（制品仓无服务端二进制）。
- 未注册 112 个：位于 `#ifdef HAVE_MYSQL` / `#ifdef HAVE_PGSQL` 条件块内
  （`bulk_lease_query4` 16、`bulk_lease_query6` 66、`lease_query4` 10、
  `lease_query_impl6` 20）；其中 56 个 PgSQL 用例已在上述可选后端配置下执行，
  56 个 MySQL 用例因制品仓无服务端二进制无法运行

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/kea/hooks/libdhcp_lease_query.so` | lease-query hook 插件（与上游安装路径一致） |
| `lib/libkea-*.so*` | 插件运行时依赖的 20 个 Kea 库（`readelf -d` NEEDED 闭包） |
| `licenses/COPYING` | 上游许可证（MPL-2.0） |
| `patches/` | 2 个平台适配补丁 |

## 注意事项

- **hook 不被链接**：`libdhcp_lease_query.so` 由 kea-dhcp4/kea-dhcp6 在运行时
  `dlopen()` 加载，`package_info()` 因此不导出可链接库与头文件，仅保留
  `libdirs` 以便消费环境定位 Kea 运行库。
- **RPATH**：插件 RUNPATH 保持上游语义（`LIBDIR_INSTALLED`，conan 下为 `/lib`），
  依赖解析沿用 Kea 的部署约定（进程内 dlopen 时符号已由服务器解析，
  独立加载时经 `LD_LIBRARY_PATH`，Conan 的 runenv 已提供）。
- **完全构建**：Kea 单 Meson 工程构建全部目标（含其它 hook 与服务器二进制），
  配方只打包本 hook 与其运行时依赖闭包，不混入其它组件产物。
- **测试范围**：只运行覆盖本 hook 的两个套件；Kea 全量测试需要特权与网络
  夹具，且与本插件无关，不在本包范围内。
- **鸿蒙特有测试 1 项**（`test_package/test_ohos_platform.c`）：上游两个 gtest 套件只验证 hook
  逻辑，不校验产物平台 ABI；该用例补充校验 OHOS aarch64/musl/libc++ 平台签名（`EM_AARCH64`、
  `DT_NEEDED` 为 `libc.so` 而非 glibc 的 `libc.so.6`、`libc++_shared.so`）与 OHOS 加载器
  `dlopen(RTLD_NOW)` 可解析性，本机 OHOS aarch64 实测 1/1 通过（见上）。
---

**编译结束**: 2026-09-20 12:xx
**最终状态**: built
