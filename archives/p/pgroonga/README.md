# pgroonga — 基于 Groonga 的 PostgreSQL 全文检索扩展

## 概述

PGroonga（pgroonga/pgroonga，PostgreSQL 许可证）把 [Groonga](https://groonga.org/)
的全文检索能力做成 PostgreSQL 的 **index access method**。它不是一个独立
服务，而是一组 PostgreSQL `shared_module` + 扩展安装脚本：

- `pgroonga` —— 主体。注册 `USING pgroonga` 索引访问方法，提供
  `&@`（全文检索）、`&@~`（Groonga 查询语法）、`&^`（词项前缀）、`&~`（正则）
  等运算符，以及 `pgroonga_score` / `pgroonga_highlight_html` /
  `pgroonga_query_extract_keywords` / `pgroonga_tokenize` 等函数；
- `pgroonga_database` —— 数据库级管理函数（Groonga 数据库的导出/清理等）；
- `pgroonga_check` —— 索引与 Groonga 存储的一致性检查；
- `pgroonga_crash_safer` / `pgroonga_wal_applier` /
  `pgroonga_wal_resource_manager` / `pgroonga_standby_maintainer` —— 让
  Groonga 自身的存储与 PostgreSQL WAL（含流复制）保持一致。

它支持多语言全文检索（分词靠 Groonga 的 `TokenNgram` / `TokenBigram`，
归一化靠 `NormalizerNFKC*`，都是 Groonga 内置实现），也支持 JSONB 与
词项/前缀检索，是不依赖外部搜索引擎的纯扩展方案。

**本仓库适配版本**：4.0.8（HarmonyOS PC aarch64 + PostgreSQL 18.3）

## 功能概述

```sql
CREATE EXTENSION pgroonga;

CREATE TABLE memos (id integer PRIMARY KEY, content text);
CREATE INDEX memos_content_idx ON memos USING pgroonga (content);

-- 全文检索
SELECT * FROM memos WHERE content &@ 'Groonga';
-- Groonga 查询语法
SELECT * FROM memos WHERE content &@~ 'rdbms OR engine';
-- 打分
SELECT pgroonga_score(tableoid, ctid), * FROM memos WHERE content &@ 'Groonga';
```

本包产物（不安装进 PostgreSQL 安装目录）：

```
lib/pgroonga.so                          索引访问方法 + 运算符 + 函数
lib/pgroonga_check.so                    pgroonga_check 管理函数
lib/pgroonga_database.so                 数据库管理模块
lib/pgroonga_crash_safer.so              崩溃后 Groonga 索引一致性
lib/pgroonga_wal_applier.so              WAL 回放
lib/pgroonga_wal_resource_manager.so     WAL 资源管理
lib/pgroonga_standby_maintainer.so       备库维护
share/extension/pgroonga.control
share/extension/pgroonga--4.0.8.sql
share/extension/pgroonga_database.control
share/extension/pgroonga_database--4.0.8.sql
```

## OHOS 适配要点

1. **PostgreSQL 走 `tool_requires("postgresql/18.3")`**。CI 的 `-pr:b` 与
   `-pr:h` 是同一个 OHOS profile，因此 tool_requires 直接解析到 ohpcd 已发布
   的 OHOS 制品，构建期一次下载即得到 `include/postgresql/server/`（服务端
   头）、`lib/postgresql/`（pkglibdir + pgxs + `pg_regress`）与
   `initdb`/`pg_ctl`/`postgres`/`psql` 全套服务端二进制，不需要在 `build()` 里
   自举 PG 源码树。
2. **`pg_config` shim**。上游 meson 通过 `pg_config --includedir-server` /
   `--pkglibdir` / `--sharedir` / `--bindir` / `--cppflags` / `--cflags_sl`
   反查安装位置，而 Conan 打的 postgresql 是 DESTDIR 可重定位安装（configure
   前缀为空），`pg_config` 会回 `//include/postgresql/server`、`//lib` 这类
   指向文件系统根而非包目录的路径。`generate()` 生成一个只重定向「路径类」
   查询的 shim，其余参数原样转发给真 `pg_config`。
3. **groonga 的 `.pc` 烘焙了构建机前缀**，必须由 Conan 重新生成：配方
   `generators = "PkgConfigDeps"`，`MesonToolchain` 自动把 generators 目录
   写进 `pkg_config_path`。
4. **`-Dinstall_to_postgresql=false` + `-Ddatadir=share`**：模块落包内 `lib/`，
   扩展脚本落 `share/extension/`。`MesonToolchain` 默认把 `datadir` 设为
   `resdirs[0]`，不显式改回 `share` 会得到 `share/res/extension` 这种 PG
   找不到的路径。
5. **运行期靠集群参数发现扩展**：`extension_control_path`（PG 18+）指向
   `share/extension`，`dynamic_library_path` 指向 `lib`。PG 18 的
   `load_external_function` 对「简单名」（`$libdir/` 之后不再出现目录分隔符）
   会剥掉前缀交给 `dynamic_library_path` 搜索，所以
   `module_pathname = '$libdir/pgroonga'` 无需改写 —— 本包因此**不带任何补丁**。
6. **`-Dtest=false`**：上游 `-Dtest=true` 会硬 `find_program('ruby')` 跑
   `test/prepare.rb` 生成 pg_regress schedule，OHOS 无 ruby。回归改在
   `test_package` 里用 PG 官方 `pg_regress` 驱动，schedule 由 Python 复刻
   `prepare.rb` 生成 —— 用例集合与上游一致，不是人工挑选的子集。
7. **`GRN_PLUGINS_DIR`**：groonga 的插件目录是编译期烘焙进 `libgroonga.so`
   的（那是构建机路径），设备上不存在，运行期需覆盖。

## 依赖关系

- 编译依赖：`groonga/16.0.8`（检索引擎）、`msgpack/7.0.1`、`libxxhash/0.8.3`
- 构建期工具：`postgresql/18.3`（`tool_requires`）
- 运行依赖：`groonga/16.0.8` 及其传递依赖的共享库（`libgroonga.so` 等），
  由 PostgreSQL 服务端进程 `dlopen`

## 参考链接

- 上游文档：https://pgroonga.github.io/
- 本仓库版本笔记：`4.0.8/notes.md`
- 测试形态声明：`4.0.8/test_package/MANIFEST.yml`
- 回归排除清单：`4.0.8/test_package/regress-skip.txt`
