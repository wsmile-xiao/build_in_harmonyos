# libsqlite3 3.50.0 适配记录

## 适配范围

- 上游项目：`https://www.sqlite.org/`
- 官方归档：`sqlite-autoconf-3500000.tar.gz`
- SHA-256：`3bc776a5f243897415f3b80fb74db3236501d45194c75c7f69012e4ec0128327`
- Conan 包：`libsqlite3/3.50.0`；库名和上游 CMake/pkg-config 名仍为 `sqlite3`

## 构建配置

SQLite 官方 autoconf bundle 直接提供 amalgamation。OHOS HMDFS 上不调用
autosetup 的 jimsh0 子进程生成器，配方从 Conan 工具闭包取得 clang 与 llvm-ar，
编译静态 `libsqlite3.a` 和 `sqlite3` CLI，并保留 `dl`/`pthread`/`m` 系统库边界；
其中 shell 与 FTS5 的 `ceil`、`floor`、`log` 符号要求 Unix-like 链接器显式使用
`-lm`；静态库消费者也必须从 `cpp_info.system_libs` 继承该系统库。

## 测试设计

### 上游测试（Tcl 回归套件，全量真实执行）

上游完整源码树 `sqlite/sqlite` tag `version-3.50.0` 携带 Tcl 回归套件（官方
autoconf 发行包不含该目录，套件自上游仓库取得）。用例口径：`test/*.test`
文件 = 1 用例（与审查实测 N=1162 一致），共 1162 个 = 1154 个叶子用例文件
（含 `do_test` 断言）+ 8 个套件调度驱动（自身 0 断言）。testfixture 以与本
配方一致的编译开关构建后，非 root 用户逐文件执行：叶子 1154/1154 全部
`0 errors`，`do_test` 子测试 1,413,931 次执行；8 个驱动按标准入口执行，
逐文件结果、失败定位与偏差消除过程见 `reports/upstream-test-evidence.md`。

### 消费者端到端用例（OHOS aarch64 真机口径）

- `test_package/test.c`：3 个完整消费者端到端用例（文件库持久化 CRUD 生命周期 10 断言、查询引擎路径含 FTS5+RTREE 7 断言、版本与编译特性契约 7 断言）
- `test_package/conanfile.py`（`_cli_e2e`）：打包 `sqlite3` CLI 端到端流程（建库写数 → `.dump` 导出并校验 → 重导入 → 守卫触发器校验两个库）5 个校验点

本地交叉验证（qemu-aarch64-static + OHOS musl runroot，与 CI Worker 同口径）：
`RESULT: 24 checks, 0 failures`；`cli e2e: create -> .dump -> re-import -> verify (both DBs) OK`。

## 平台验证

本地交叉验证以 `host=ohos-aarch64-run`、`build=default` 执行；`conan create`
EXIT=0，静态库与 `sqlite3` CLI 打包成功，消费者端到端用例全部通过。

---

**编译结束**: 2026-09-24
**最终状态**: built
