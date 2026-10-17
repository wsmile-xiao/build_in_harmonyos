# pgtap 1.3.4 适配笔记（OHOS PC aarch64）

## 一句话

PostgreSQL 的 TAP 单元测试扩展（纯 SQL / PLpgSQL：1000+ 断言函数 + `runtests` 驱动器）。
使用上游 PGXS 构建，**零源码补丁**（`patches/` 不存在）；制品为 `extension/` 下的控制文件、
安装/升级 SQL 与 pgtap-core / pgtap-schema / uninstall 拆分件，无编译产物。

## 上游信息

| 项 | 值 |
|----|----|
| 上游仓库 | https://github.com/theory/pgtap |
| 版本 / tag | 1.3.4 / `v1.3.4` |
| tarball | https://github.com/theory/pgtap/archive/refs/tags/v1.3.4.tar.gz |
| sha256 | `d2c951afb296a001d21785611a8e966e3f8fa3f5bfbd929396a5130c0152f314` |
| 语言 / 构建系统 | SQL/PLpgSQL + Perl 生成脚本 / PGXS（PostgreSQL Extension Building Infrastructure） |

## W0：依赖核查（结论：依赖已发布，无 R36 阻塞）

- `conan download postgresql/18.3 -r=ohpcd --only-recipe` + 完整下载：成功。解包核对：
  `bin/pg_config`、`lib/postgresql/pgxs`、`include/postgresql/server/postgres.h`、
  `bin/{postgres,initdb,pg_ctl,createdb,psql}` 齐备 —— 完整 server+client 安装，无需 vendor PG 源码树。
- `conan download perl/5.42.2.3 -r=ohpcd --only-recipe` + 完整下载：成功。`bin/perl --version`
  在设备可直接运行（`This is perl 5, version 42, subversion 2 ... aarch64-linux-thread-multi`）。
- 结论：两个 tool_requires 均已发布，直接进入适配主流程。

## 构建

```bash
# 配方内 build() 实际执行（PGXS，无 configure 步骤）
PERL5LIB="<perl 包>/lib/perl5" make \
  PG_CONFIG="<postgresql 包>/bin/pg_config" \
  PERL="<perl 包>/bin/perl" OSNAME=harmonyos -j<CPU 数> all
```

`make all` 生成：`sql/pgtap.sql`（1085 个函数定义）、`sql/pgtap--1.3.4.sql`、
`sql/{pgtap-core,pgtap-schema}--1.3.4.sql`、`sql/uninstall_pgtap.sql`、17 个历史升级脚本。
`package()` 按上游 `make install` 的 DATA 清单复制到包内 `extension/`，并 vendor 上游回归资产到
`upstream/`（test/sql、test/expected、setup/psql/schedule、静态 pgtap.sql）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan perl 生成 gencore 时报 `Can't locate strict.pm in @INC (//lib/perl5/...)` | conan perl 包按空前缀安装，内建 @INC 指向 `//lib/...` | 构建命令前置 `PERL5LIB=<perl包>/lib/perl5` |
| 2 | `os_name()` 生成空串（会破坏上游 util.sql 的 `matches(os_name(), '^[[:alnum:]]+$')`） | 上游 `tools/getos.sh`（Perl Configure 的 uname 解析器）在设备 shell 下报 `alias: -e: invalid alias name` 并输出空串（其内部 `command -v sed` 取到的是别名定义） | make 命令行显式 `OSNAME=harmonyos`（上游文档化变量）：设备与 CI 产物一致、平台标识真实 |
| 3 | conan-verify 的 G2 下载失败（ghfast.top 连接超时） | conan-verify 本地会把 `https://github.com` 前缀改写为 `https://ghfast.top/https://github.com`（E017 预防）；设备网络不可达该镜像 | `source()` 通用回退：URL 带镜像前缀时先试镜像，失败则剥离前缀改用内嵌官方 URL（sha256 覆盖同一份字节）；CI 无注入时走原路径 |
| 4 | 需要跑上游回归但 `postgresql/18.3` 包内没有 `pg_regress` | 制品包只含 server+client 工具（35 个），不含回归驱动 | test_package 复刻 pg_regress 的等价调用：`psql -X -a -q` 从 stdin 读脚本、合并 stdout+stderr、与 `test/expected/*.out` 逐字节比对（支持 `_N.out` 备用） |
| 5 | `extension.sql` 组无法执行 | 该组依赖 `citext`/`isn`/`ltree`，`postgresql/18.3` 不含 contrib 扩展 | 与上游 Makefile 在 `MISSING_EXTENSIONS` 下的排除逻辑一致地跳过（非静默忽略：结果 JSON 记录跳过原因） |

## 源码修改

无。PG 18.3 满足 Makefile 中全部版本门槛，所有 `compat/install-*.patch`（面向 PG <= 10）均不触发；
`patches/` 不存在。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| postgresql | 18.3 | `tool_requires`：pg_config + PGXS + 服务端头 + 回归测试用服务端二进制 |
| perl | 5.42.2.3 | `tool_requires`：`compat/gencore` 与 uninstall SQL 生成 |

## 上游测试清点与实测（R51）

| 项 | 数量 | 说明 |
|----|------|------|
| `test/sql/*.sql` 测试组 | 37 | Makefile `ALL_TESTS`（排除 schedule 生成的 build/create/update） |
| schedule 生成 setup 组 | 2 | build（语法检查，回滚）/ create（CREATE EXTENSION） |
| expected 输出文件 | 54 | 含 `_1.._6` 备用输出（继承/runjusttests 等） |
| **实测执行** | **38/38 逐字节通过** | 36 个测试组 + build/create，`psql -X -a -q` stdin + 逐字节比对 |
| 跳过 | 1 | `extension.sql`（citext/isn/ltree 不在 postgresql/18.3，选型原因见上表 #5） |
| 不可执行 | 1 | `update.sql` 属 `make updatecheck`（需联网从 PGXN 装 pgtap 0.95.0 再 ALTER EXTENSION UPDATE），不在 `make installcheck` 内 |

消费者/鸿蒙特有测试：17 项（8 项制品断言 + 9 项 SQL/TAP 断言，含"故意失败断言必须报 not ok"负向对照），
随 `conan create` 的 test 阶段实跑，全部通过。

## 验证结果

```bash
conan create . -pr:b=ohos-aarch64-device -pr:h=ohos-aarch64-device
# exit 0：17/17 本地断言；上游 38/38 组逐字节通过（extension.sql 跳过）

python3 scripts/ohc-run.py conan-verify pgtap 1.3.4 --profile ohos-aarch64-device
# G0-G4 + L2/L4/L5 全部 PASS
```

本地 CI（W3）与 conan-verify 报告见 `reports/w3-local-ci.log`、`reports/conan-verify-report.md`（不入库）、
`.ci-result.json`（工具生成）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `packaging/pgtap-1.3.4-ohos-aarch64.tar.gz` | 见 packaging/ | 由 conan 包目录原样打包（extension/ + upstream/ + doc/） |
| `extension/pgtap.control` | 168 B | 扩展控制文件（default_version=1.3.4, requires=plpgsql, relocatable） |
| `extension/pgtap--1.3.4.sql` | 370926 B | 安装脚本（1085 个 CREATE OR REPLACE FUNCTION） |
| `extension/pgtap--*--*.sql` | 18 个 | 0.90.0→1.3.4 历史升级链 + unpackaged |

## 注意事项

1. `os_name()` 在构建时钉为 `harmonyos`；上游测试仅要求 `^[[:alnum:]]+$`，对具体值无断言。
2. 本包为纯数据扩展（无 bin/lib/include）：CI L1e 破坏性反向验证会因无标准产物目录而跳过；
   test_package 以正向 `CREATE EXTENSION` + 负向对照（故意失败断言必须报 `not ok`）保证测试对包的实质依赖。
3. PostgreSQL 18 起可用 `extension_control_path=<包目录>:$system` 免拷贝加载扩展（消费方式见 README.md）。
4. 上游发布 tarball **不含 LICENSE 文件**（许可证以 META.json / 配方 `license` 字段声明），
   因此包内没有 licenses/ 目录 —— 与上游 `make install` 的实际文件集一致。
---

**编译结束**: 2026-10-01 18:19
**最终状态**: built
