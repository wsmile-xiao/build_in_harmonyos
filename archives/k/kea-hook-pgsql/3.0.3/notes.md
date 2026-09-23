# kea-hook-pgsql 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（=1.11.0，`tool_requires`）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18 + `ci/conan/profiles/ohos-aarch64`）
- 状态: built（conan create 通过；未 push、未 upload）

## 软件定位
- 上游：ISC Kea 3.0.3（MPL-2.0），本库源码目录 `src/hooks/dhcp/pgsql/`（hook 本体）与 `src/lib/pgsql/`（libkea-pgsql 连带库）
- 产物：`libdhcp_pgsql.so`（hook 插件，安装到 `lib/kea/hooks/`，由 kea-dhcp4/kea-dhcp6 运行时 dlopen）+ `lib/libkea-pgsql.so.88`（PostgreSQL 连接/交换封装）+ `share/kea/scripts/pgsql/*.pgsql`（建库/删库 schema 数据脚本）
- 功能面：PostgreSQL 配置后端（config backend DHCPv4/v6）、host data source、forensic log、lease manager
- 构建方式：Kea 3.0 起 Autotools → Meson，整棵源码树单工程构建；本配方构建上游树后只打包本插件 + 其 NEEDED 闭包中的 21 个 Kea 运行库（含 libkea-pgsql）+ schema 数据脚本

## 编译步骤

```bash
# 1) 生成构建环境（PkgConfigDeps + MesonToolchain，见 conanfile.py generate()）
conan install . --output-folder=<out> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 2) 配置
meson setup <builddir> <srcdir> --native-file=<out>/conan_meson_native.ini -Dtests=enabled
# 3) 构建（hook + libkea-pgsql + 测试 target，随上游树依赖闭包连带完成）
ninja -C <builddir> -j6 \
  src/hooks/dhcp/pgsql/libdhcp_pgsql.so \
  src/hooks/dhcp/pgsql/libloadtests/dhcp-pgsql-libload-tests
# 4) 上游无需数据库的套件（build() 内执行的就是它）
meson test -v -C <builddir> dhcp-pgsql-libload-tests
# 5) 完整制品验证
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题（首个错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]`（exit 1） | meson 对 clang 默认用裸名 `llvm-ar` 探测静态链接器，Conan MesonToolchain 未写出 `ar/ranlib`，本环境（及 CI）裸名 exec 失败 | `generate()` 从 `tools.build:compiler_executables.c` 推导同目录 `llvm-ar`/`llvm-ranlib` 写入 `tc.binaries` |
| 2 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".`（exit 1） | OHOS 上 `build_machine.system()` 返回 `harmonyos`，Kea 平台白名单（`meson.build:163-186`）不含它 | 补丁 0001：顶层 `meson.build` 把 `harmonyos` 归一化为 `linux`（一处修改使所有子目录走 Linux 分支） |
| 3 | `meson.build:477:8: ERROR: Problem encountered: Boost TLS support broken.`（meson-log 首个编译错误 `boost/core/detail/sp_thread_sleep.hpp:73:5: error: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl `<pthread.h>` 不声明 `pthread_setcancelstate()`，而 boost 1.85 在 `BOOST_HAS_PTHREADS && !__ANDROID__` 时无条件调用 | `tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")`（boost 官方逃生宏） |
| 4 | `Checking if "LOG4CPLUS_INITIALIZER_H" with dependency log4cplus runs: NO (127)` → `meson.build:824:24: ERROR: Unknown variable "log4cplus".` | meson 特性探针是"编译并运行"，host 共享依赖 `liblog4cplus.so.9` 不在配置期运行时 `LD_LIBRARY_PATH`（127 = 动态加载失败） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")`（聚合进 conanbuild.sh） |
| 5 | `src/lib/dhcp/iface_mgr_linux.cc:40:10: error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 `linux/socket.h`（bionic 派生）定义 `struct sockaddr_storage`，与 musl `sys/socket.h` 冲突；`linux/rtnetlink.h` 间接包含前者 | 补丁 0002：包含 netlink 头前 `#define sockaddr_storage __linux_uapi_sockaddr_storage`、include 后 `#undef`，守卫 `__linux__ && !__GLIBC__`（标准 libc 鉴别宏，不使用 `__OHOS__`） |
| 6 | `Dependency "libpq" not found but postgresql enabled`（本包相对 stat-cmds 的增量问题） | `-Dpostgresql=enabled` 时 `POSTGRESQL_DEP = dependency('libpq', method: 'pkg-config')`（`src/hooks/dhcp/pgsql/meson.build:1` 与 `src/lib/pgsql/meson.build:1`），需有可用的 `libpq.pc` | `requires("libpq/18.6")`（conan 配方 `pkg_config_name="libpq"`）+ `PkgConfigDeps(self).generate()` 生成 `.pc`；libpq 运行时 `.so` 亦加入配置期 `LD_LIBRARY_PATH` |

说明：问题 1-5 与 kea-hook-stat-cmds 3.0.3 完全同源（同一上游源码树同一版本），
两个补丁文件与 stat-cmds 的补丁逐字节一致；增量面是问题 6（libpq）与
`-Dpostgresql=enabled`（本包构建目标 `src/hooks/dhcp/pgsql` 的使能开关）。

## 源码修改

| 补丁文件 | 修改文件 | 改动 | 说明 |
|---|---|---|---|
| `patches/0001-meson.build.patch` | `meson.build` | +6/-0 | 平台名归一化（harmonyos → linux），无平台宏 |
| `patches/0002-src-lib-dhcp-iface_mgr_linux.cc.patch` | `src/lib/dhcp/iface_mgr_linux.cc` | +13/-0 | netlink 头前重命名 UAPI `sockaddr_storage`，守卫 `__linux__ && !__GLIBC__` |

## 依赖版本

| 依赖 | 版本 | 类型 |
|---|---|---|
| boost | 1.85.0 | 强制（`>=1.66`；1.90/1.91 制品仓包缺 Kea 实际使用的头文件） |
| log4cplus | 2.2.0.1 | 强制（经 kea-log 传递 + 顶层 fallback 声明） |
| openssl | 3.5.8.1 | 强制（`crypto` 默认后端，Mandatory） |
| libpq | 18.6 | 强制（`-Dpostgresql=enabled` 的 pkg-config 依赖；archives/l/libpq，conan 配方 `pkg_config_name="libpq"`） |
| gtest | 1.17.0.1 | test_requires（`-Dtests=enabled`） |
| meson | 1.11.0 | tool_requires（须 ≥1.10，boost 包头不含 `libboost_system`，靠 header-only 模块回退） |
| zlib | 1.3.1 | 传递（boost 依赖） |

可选后端 botan/krb5/mysql/netconf 显式 `disabled`（制品仓无可消费依赖，本包不需要）。

## 知识图谱

| 平台问题 | 命中/新增 |
|---|---|
| `Unknown linker(s): [['llvm-ar']]` | E481（MesonToolchain 注入 llvm-ar/llvm-ranlib）、E012 |
| `Unsupported system "harmonyos"` | E090 |
| `pthread_setcancelstate` 未声明 | E085 / E127 / E507 |
| `sockaddr_storage` 重定义 | E091 / E119 |
| 配置期 compile-and-run 探针 `runs: NO (127)` | E429 |
| `Dependency "libpq" not found but postgresql enabled` | libpq 包 `pkg_config_name="libpq"` + PkgConfigDeps 即可解析（复用既有模式，无新增条目） |

## 上游测试

三个 Meson 注册的 gtest 套件：

| 套件 | 用例 | DB 需求 | 结果 |
|---|---|---|---|
| `dhcp-pgsql-libload-tests` | 3 | 无 | build() 内真实执行（meson test），3/3 通过，0 失败 0 跳过 |
| `dhcp-pgsql-lib-tests` | 602（另 4 个 DISABLED 为上游自带） | 活体 PostgreSQL + keatest schema | 602/602 通过（设备侧活体 PG 18.3 实测，exit 0） |
| `kea-pgsql-tests` | 47 | 活体 PostgreSQL + keatest schema | 47/47 通过（设备侧活体 PG 18.3 实测，exit 0） |

### DB 套件的测试夹具（按上游 `doc/devel/unit-tests.dox` pgsqlUnitTestsPrerequisites 节）

在 OHOS 设备侧用制品仓 `postgresql/18.3` 包提供的真实 PostgreSQL 服务器搭建：

1. 用户 `keatest` / `keatest_readonly`，口令 `keatest`；数据库 `keatest`；
   `GRANT ALL PRIVILEGES ON DATABASE keatest TO keatest`；`GRANT ALL PRIVILEGES ON SCHEMA public TO keatest`（PG15+ 需显式）。
2. schema 以 `keatest` 身份加载 `dhcpdb_create.pgsql`；随后以 `keatest` 执行
   `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES to keatest_readonly`
   与上游文档给出的已知问题对策 `GRANT SELECT ON ALL TABLES IN SCHEMA public TO keatest_readonly`。
   测试框架默认 soft-wipe（`KEA_TEST_DB_WIPE_DATA_ONLY` 未设时每用例只清数据、不重建 schema），
   授权在整个运行期保持有效。
3. `pg_hba.conf` 必须为密码认证（scram-sha-256），不能是 trust：`OpenDatabase`
   三例验证"错误口令必须被拒绝（DbOpenError）"，trust 下错误口令可登录导致假失败。
4. 本内核禁止创建 AF_UNIX socket（`Operation not permitted`），`postgresql.conf`
   置 `unix_socket_directories = ''` 走纯 TCP（测试串即 `-h localhost`，不受影响）。

### 首轮（trust + 缺 readonly 授权）6 例失败的归因与复跑结论

首轮实测 596/602 通过，6 例失败全部归因于测试夹具而非移植缺陷：

| 失败用例 | 现象 | 归因 | 夹具修复后 |
|---|---|---|---|
| `PgSqlHostDataSource.OpenDatabase` / `...MultiThreading`、`PgSqlOpenTest.OpenDatabase` | 期望错误口令抛 `DbOpenError`，实际登录成功 | `pg_hba.conf` 为 trust，口令校验被跳过（上游文档明确要求 md5/密码认证） | 3/3 通过 |
| `PgSqlHostDataSourceTest.testReadOnlyDatabase` / `...MultiThreading` | 只读用户 SELECT `schema_version` 报 `permission denied` | `keatest_readonly` 未按上游文档创建并授权（文档还给出 PG 新版的已知问题与对策） | 2/2 通过 |
| `PgSqlLeaseMgrDbLostCallbackTest.testRetryOpenDbLostAndRecoveredAfterTimeoutCallbackMultiThreading` | 重试回调计数 2/3 与期望 1/2 不符（时序敏感） | 设备高负载（load 20+）下的时序抖动，单线程版同类用例通过 | 通过（1/1） |

按上游文档修正夹具后全量复跑（r2 轮）：`dhcp-pgsql-lib-tests` 602/602、
`kea-pgsql-tests` 47/47、`dhcp-pgsql-libload-tests` 3/3，0 失败。

## 验证结果

```bash
# 构建
ninja -C <builddir> -j6 <pgsql hook + libload test target>
# → exit_code=0

# 上游无需 DB 的套件
meson test -v -C <builddir> dhcp-pgsql-libload-tests
# → Ok: 1  Fail: 0（3/3 用例通过：validLoad4/validLoad6/invalidDaemonLoad）

# 上游 DB 套件（活体 PostgreSQL 18.3 + keatest schema，设备侧实测）
./dhcp-pgsql-lib-tests → [==========] 602 tests from 21 test suites ran. [  PASSED  ] 602 tests.（exit 0）
./kea-pgsql-tests      → [==========] 47 tests from 4 test suites ran. [  PASSED  ] 47 tests.（exit 0）

# conan create（含 build() 内上游测试 + test_package dlopen 实测）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → exit_code=0（1478 目标全量构建；build() 内 libload 3/3 PASSED；
#    test_package：test_pgsql_hook 契约 1/1 + test_ohos_platform OHOS 平台断言全 ok）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/kea/hooks/libdhcp_pgsql.so` | 本 hook 插件 |
| `lib/libkea-*.so*`（21 个库） | 插件运行时加载的 Kea 共享库（`readelf -dW` NEEDED 闭包），含 soname 符号链接，含 `libkea-pgsql.so.88` |
| `share/kea/scripts/pgsql/dhcpdb_create.pgsql` / `dhcpdb_drop.pgsql` | 建库/删库 schema 数据脚本（上游安装到 `share/kea/scripts/pgsql`） |
| `licenses/COPYING` | 上游 MPL-2.0 许可 |

## 注意事项

- 本包**不导出可链接的库/头**（`cpp_info.libs=[]`、`includedirs=[]`）：插件由 Kea 服务器运行时 `dlopen()`，不是被链接的目标；`libdirs=["lib"]` 仅供消费者运行时环境指向包内 Kea 库；运行期另需 `libpq.so.5`（本包 libpq 依赖提供）。
- 本包无 CLI 产物 → 不需要 `commands.json`（R38 不适用）。
- boost 必须固定 1.85.0：制品仓 `1.90.0.x` 缺 `boost/interprocess/sync/interprocess_upgradable_mutex.hpp`、`1.91.0.1.3` 缺 `boost/circular_buffer.hpp`（Kea `meson.build:198-215` 的 required 头检查）。
- 不运行整棵 Kea 测试套件（需要 root/网络夹具），只跑覆盖本插件的三个 Meson 注册套件。
- `wipe_data.sh` / `upgrade_*.sh` 是 `configure_file()` 产物、内嵌构建期前缀，故不随包发布（schema 数据脚本 `*.pgsql` 为纯数据文件，随包发布）。
- 复现 DB 套件需按上文夹具小节准备活体 PostgreSQL；`build()` 只执行无需数据库的 `dhcp-pgsql-libload-tests`（与 stat-cmds 配方同约定）。
---
