# sqlite3 3.53.4 适配记录

## 适配范围

- 上游项目：`https://www.sqlite.org/`
- 官方归档：`sqlite-autoconf-3530400.tar.gz`
- SHA-256：`0e9483900e92cd5de8fd48d16bf9200145a61f7fd5be542a5ac81d8a9516eb9c`
- Conan 包：`sqlite3/3.53.4`

## 构建配置

SQLite 官方 autoconf bundle 直接提供 amalgamation。OHOS HMDFS 上不调用
autosetup 的 jimsh0 子进程生成器，配方从 Conan 工具闭包取得 clang 与 llvm-ar，
编译静态 `libsqlite3.a` 和 `sqlite3` CLI，并保留 `dl`/`pthread`/`m` 系统库边界；
其中 shell 与 FTS5 的 `ceil`、`floor`、`log` 符号要求 Unix-like 链接器显式使用
`-lm`；静态库消费者也必须从 `cpp_info.system_libs` 继承该系统库。

## 测试设计

`test_package/test.c` 调用 SQLite C API，覆盖建表、插入、查询、行值校验和版本
校验，共 7 个断言。官方归档不含独立 Tcl `test/` 目录，因此上游测试分母为 0；
CLI smoke 使用固定 SQL 验证版本和查询结果。

## 平台验证

前一候选 `w3-r001` 已完成一次 native self-sign 后的 OHOS AArch64 消费者执行，
但本次为满足 Conan G1 补齐 `export_sources()` 与补丁应用入口，候选树发生变化。
该回执保持不可变，仅作诊断历史；变更后的候选必须使用新的 W3 run 重新传输、签名
和唯一启动。
---

**编译结束**: 2026-09-04 21:29
**最终状态**: built
