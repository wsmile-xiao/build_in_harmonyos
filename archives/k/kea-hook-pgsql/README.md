# kea-hook-pgsql

ISC Kea 的 **PostgreSQL 后端** hook 插件，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`libdhcp_pgsql.so` 是 Kea DHCP 服务器的 PostgreSQL 后端钩子：为 `kea-dhcp4`/`kea-dhcp6`
提供配置后端（config backend DHCPv4/DHCPv6）、主机保留数据源（host data source）、
法务日志（forensic log）、租约管理器（lease manager）的 PostgreSQL 存储，并连带提供
Kea 的 PostgreSQL 连接/交换封装库 `libkea-pgsql.so`。插件由 Kea 服务器在运行时
`dlopen()` 加载（`hooks-libraries` 配置项），不是被链接的库。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/hooks/dhcp/pgsql/`（hook 本体）与 `src/lib/pgsql/`（libkea-pgsql，
  同一 Kea 源码树，Meson 单工程构建）
- 安装路径：`lib/kea/hooks/libdhcp_pgsql.so`、`lib/libkea-pgsql.so.*`、
  `share/kea/scripts/pgsql/*.pgsql`（建库/删库 schema 脚本）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件，须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端（`CRYPTO_DEP`） |
| libpq | 18.6 | 强制；PostgreSQL 客户端库（`-Dpostgresql=enabled`，经 pkg-config `libpq` 解析） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带插件运行时加载的 21 个 Kea 共享库（`readelf -d` NEEDED 闭包，含
libkea-pgsql），因此安装后无需额外的 Kea 运行库即可被服务器加载；运行期还需
`libpq.so.5`（由本包的 libpq 依赖提供）与可达的 PostgreSQL 服务器。

## OHOS 适配要点

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 用 `build_machine.system()`
   做平台分支且白名单不含它 → 顶层 `meson.build` 归一化为 `linux`，使
   `iface_mgr_linux.cc` / `pkt_filter_lpf.cc` 等 Linux 后端源码被选中。
2. **UAPI 头冲突**：OHOS 的 `linux/socket.h` 与 musl `sys/socket.h` 都定义
   `struct sockaddr_storage` → 包含 netlink 头时用 define-guard 重命名内核侧
   定义（`__linux__ && !__GLIBC__` 守卫，无需平台宏）。
3. **boost/musl 差异**：musl `pthread.h` 无 `pthread_setcancelstate` 声明 →
   定义 boost 官方逃生宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
4. **Meson 工具链**：需同时使用 `PkgConfigDeps`（依赖 `.pc`）与
   `MesonToolchain`；配置期 `cpp.run()` 探针要求 host 共享依赖在
   `LD_LIBRARY_PATH` 可见；`llvm-ar`/`llvm-ranlib` 从编译器路径推导为绝对路径。
5. **PostgreSQL 使能**：`-Dpostgresql=enabled` 经 pkg-config 探测 `libpq`，
   由 `libpq/18.6` 依赖提供；mysql/netconf/krb5 显式 `disabled`。

## 上游测试

| 套件 | 用例 | 说明 |
|------|------|------|
| `dhcp-pgsql-libload-tests` | 3 | 插件的加载/卸载契约（validLoad4/validLoad6/invalidDaemonLoad），无需数据库，`build()` 内真实执行 |
| `dhcp-pgsql-lib-tests` | 602（4 disabled） | hook 集成测试（config backend、forensic log、host data source、lease mgr 等），需活体 PostgreSQL + keatest schema |
| `kea-pgsql-tests` | 47 | libkea-pgsql 单元测试，需活体 PostgreSQL + keatest schema |

后两个套件需要活体 PostgreSQL 服务器与按上游文档（`doc/devel/unit-tests.dox`
pgsqlUnitTestsPrerequisites 节）准备的 keatest/keatest_readonly 夹具。本版本在
OHOS 设备上用制品仓 `postgresql/18.3` 包提供的真实服务器完成了夹具并全量实测，
结果见 `3.0.3/notes.md` 与 `3.0.3/test_package/MANIFEST.yml`。

## 使用

```bash
conan install --requires=kea-hook-pgsql/3.0.3 -pr:h=<ohos-aarch64 profile>
```

Kea 服务器加载（`kea-dhcp4.conf`）：

```json
{
  "Dhcp4": {
    "hooks-libraries": [
      { "library": "<prefix>/lib/kea/hooks/libdhcp_pgsql.so" }
    ],
    "host-cache": {},
    "hosts-database": {
      "type": "postgresql",
      "name": "kea",
      "host": "127.0.0.1",
      "user": "kea", "password": "..."
    }
  }
}
```

数据库初始化使用包内 `share/kea/scripts/pgsql/dhcpdb_create.pgsql`（升级脚本
`upgrade_*_to_*.sh` 留在上游源码树，内嵌构建期前缀，不随包发布）。
