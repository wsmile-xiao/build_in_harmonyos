# libgda5 5.2.10 — 上游测试报告（HarmonyOS PC / aarch64-ohos）

## 0. 概览

| 项 | 值 |
|---|---|
| 上游测试树 | `tests/`（源码 Makefile.am 声明：39 个无条件 TESTS + 6 个条件 `+=` TESTS） |
| 本合同适用用例 | **38**（37 可运行 + 1 `providers/check_mysql` 因 MySQL provider 未启用而未构建） |
| 结果 | **35 PASS / 2 SKIP / 1 未构建 / 0 FAIL** |
| 跳过原因 | `meta-store/check_meta_store_postgresql`、`check_meta_store_mysql` 需要真实 PostgreSQL/MySQL 服务端 |
| 未适用（7 项） | `tests/ui/check_sets`、`check_raw_grid_model`（`--without-ui`）；`providers/check_bdb`、`check_firebird`、`check_mdb`、`check_oracle`、`check_postgres`（对应 provider 全部关闭） |
| 日志目录 | `/storage/Users/currentUser/Desktop/GPQworkspace/libgda5-build/upstream-test-logs/`（38 个逐用例 .log + `SUMMARY.txt`） |
| runner | `/storage/Users/currentUser/Desktop/GPQworkspace/libgda5-build/run_upstream_tests.sh` |
| 测试二进制构建日志 | `libgda5-5.2.10-logs/63-build-tests-clean-20260921-023440.log`（`make -C tests -k check`） |

## 1. 执行方式（R51 三步法）

1. **清点**：`grep -n "^TESTS\|^TESTS +=" tests/Makefile.am tests/*/Makefile.am`
   → `tests/` 9、`data-models/` 9、`meta-store/` 4（含 postgres/mysql 2 项）、`multi-threading/` 5、
   `parser/` 6、`providers/` 1+5 条件、`ui/` 2、`value-holders/` 3；`SUBDIRS = providers parser
   value-holders meta-store data-models multi-threading $(UI_EXTENSION) $(VALA_EXTENSIONS)`。
2. **运行**：`make -C tests -k check` 生成全部测试程序后，逐个直接执行（测试二进制与 `make check`
   完全相同）。说明：automake 并行测试 harness 在本平台不可用——libtool wrapper 报
   `getcwd: cannot access parent directories` → `providers/.libs/check_xxx: No such file or directory`，
   故改由 runner 在各自目录下执行 `./<case>`。
   运行环境：conan build+run env；`SQLITE_DBCREATE_PARAMS="DB_DIR=<srcdir>/tests/providers"`、
   `SQLITE_CNC_PARAMS="DB_DIR=<srcdir>/tests/providers;DB_NAME=testcheckdb"`、
   `GDA_TOP_SRC_DIR/GDA_TOP_BUILD_DIR=<srcdir>`。
3. **如实回填**：下表为逐用例实测（判 PASS=exit 0 且无 skip 标记；SKIP=输出 "not run/not executed"）。

## 2. 逐用例结果

| # | 目录 | 用例 | 结果 |
|---|---|---|---|
| 1-9 | tests/ | test-ddl-creator, test-bin-converter, test-sql-identifier, test-identifiers-quotes, test-sql-builder, test-connection-string-split, test-input-parsers, test-quark-list, test-sql-renderer | 9 PASS |
| 10-18 | tests/data-models/ | check_model_import, check_virtual, check_data_proxy, check_model_copy, check_pmodel, check_empty_rs, check_model_errors, check_vcnc, check_pivot | 9 PASS |
| 19-20 | tests/meta-store/ | check_meta_store_memory, check_meta_store_sqlite | 2 PASS |
| 21-22 | tests/meta-store/ | check_meta_store_postgresql, check_meta_store_mysql | 2 SKIP（需服务端） |
| 23-27 | tests/multi-threading/ | check_mutex, check_parser, check_cnc_lock, check_threaded_cnc, check_wrapper | 5 PASS |
| 28-33 | tests/parser/ | check_parser, check_validation, check_normalization, check_dml_comp, check_script, check_rewrite_for_default | 6 PASS |
| 34 | tests/providers/ | **check_sqlite**（建库→元数据→游标→查询→清理） | **PASS** |
| 35 | tests/providers/ | check_mysql | 未构建（MySQL provider 未启用） |
| 36-38 | tests/value-holders/ | check_holder, check_set, check_statement | 3 PASS |

## 3. test_package（消费者视角，`conan create` 内执行）

```
test_libgda: ALL PASS      # provider 发现 / 文件库连接 / CREATE+INSERT+SELECT / 值校验
test_ohos:   ALL PASS      # HarmonyOS 专项：__OHOS__ 守卫、provider .so dlopen(RTLD_NOW)、
                           #   中文+emoji UTF-8 往返、HMDFS 文件型数据库落盘与重开
```
证据：`libgda5-5.2.10-logs/84-conan-create-20260921-034932.log`（`CREATE_EXIT=0`）。

## 4. 未覆盖说明（非本库缺陷）

- MySQL / PostgreSQL provider：`mysql-client` 与 glib 存在 zlib 版本硬冲突；`--with-postgres` 需要
  `pg_config`（libpq 包不提供）。对应上游用例（`check_mysql`、2 项 meta-store）因此未构建/跳过。
- UI / Vala / Introspection / cmdtool：分别由 `--without-ui`、`--disable-vala`、默认 auto（OHOS 无
  `gobject-introspection-1.0.pc`）、`--disable-tools`（ncurses 只有静态 `libncursesw.a`）关闭，
  对应的 `tests/ui`（2 项）与 `$(VALA_EXTENSIONS)` 测试随之不适用。
- `po/` 顶层维护者检查（`intltool-update -m`，需 perl XML::Parser）不是测试用例，未计入统计。
