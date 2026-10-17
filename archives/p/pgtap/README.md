# pgtap

## 简介

pgTAP 是 PostgreSQL 的单元测试框架（"TAP for SQL"）：以纯 SQL / PLpgSQL 扩展的形式提供
TAP（Test Anything Protocol）断言 API——`plan` / `ok` / `is` / `has_table` /
`col_not_null` / `throws_ok` 等 1000+ 个测试函数，以及 `runtests` / `ckreserve` 等
测试驱动函数。使用者可以在 psql 脚本或 xUnit 风格的测试函数里直接对数据库结构、权限、
数据、触发器、分区等写断言，输出标准 TAP 文本，交给 `pg_prove`（Perl TAP harness）汇总。

## OHOS 适配

- 构建系统：PGXS（PostgreSQL Extension Building Infrastructure）。本库无 C 模块、无编译产物：
  `make all` 的产出是一组 SQL 脚本（`pgtap.sql`、版本化安装脚本、17 个历史升级脚本、
  `pgtap-core` / `pgtap-schema` 拆分件、`uninstall_pgtap.sql`），`make install` 将其装入
  PostgreSQL 的 `share/extension/`。
- `tool_requires("postgresql/18.3")`：使用 ohpcd 制品仓中已发布的完整 PostgreSQL 18.3
  安装（`pg_config` + `lib/postgresql/pgxs` + `initdb/postgres/pg_ctl/psql/createdb`），
  不向本归档 vendor PG 源码树。
- `tool_requires("perl/5.42.2.3")`：上游 `sql/uninstall_pgtap.sql` 与 `compat/gencore`
  拆分脚本是 Perl 实现；conan perl 包为空前缀安装（内建 @INC 指向 `//lib/perl5/...`），
  配方把 `PERL5LIB` 指向包内 `lib/perl5`。
- `OSNAME=harmonyos`：上游 `tools/getos.sh`（Perl Configure 的 uname 解析器）在 OHOS 下
  可能输出空串（实测设备 shell 中 `command -v sed` 返回别名定义导致 getos.sh 失败），
  会使 `os_name()` 返回空串并破坏上游 `util.sql`。配方显式钉住该 make 变量，保证设备与 CI
  产物一致且平台标识真实。
- **零源码补丁**：PG 18.3 不触发 Makefile 中任何 `compat/install-*.patch`（均面向 PG <= 10），
  `patches/` 不存在。

## 产物与消费

```
extension/pgtap.control              # 扩展控制文件
extension/pgtap--1.3.4.sql           # 安装脚本（1085 个函数）
extension/pgtap-core--1.3.4.sql / pgtap-schema--1.3.4.sql   # 版本化拆分件
extension/pgtap--*--*.sql            # 17 个历史升级脚本 + unpackaged（共 18 个）
extension/pgtap.sql                  # 未打包安装用全量脚本（unversioned）
extension/pgtap-core.sql / pgtap-schema.sql          # 拆分件（可手工安装）
extension/uninstall_pgtap.sql        # 卸载脚本
doc/pgtap.mmd                        # 上游文档
upstream/test/{sql,expected}/        # 上游回归资产（37 组 sql + 54 个 expected），供消费者 harness 执行
```

安装到某个 PostgreSQL 前缀：

```bash
cp extension/* "$($PG_CONFIG --sharedir)/extension/"
psql -c 'CREATE EXTENSION pgtap;'
```

PostgreSQL 18 起也可以不复制文件，直接把包目录作为扩展来源启动服务：

```
extension_control_path = '<包目录>:$system'
```

## 依赖

- 构建期：`postgresql/18.3`（pg_config + PGXS；test_package 另用其中的服务端二进制跑回归）、
  `perl/5.42.2.3`（生成 uninstall / core / schema SQL）
- 运行期：无（纯 SQL 扩展，仅依赖 PostgreSQL 自带的 `plpgsql`）

## 测试

- 上游 pg_regress 用例组逐字节执行：36 个测试组 + build/create 两个 setup 组全部通过；
  `extension.sql` 因 `citext`/`isn`/`ltree` 不在 postgresql/18.3 中而排除（与上游 Makefile
  在 MISSING_EXTENSIONS 下的排除逻辑一致）；`update.sql` 属 `make updatecheck`（需联网从
  PGXN 装旧版 0.95.0），不可离线执行。
- 消费者断言（含负向对照）见 `1.3.4/reports/test-report.md`。

## 参考

- https://pgtap.org/
- https://github.com/theory/pgtap
