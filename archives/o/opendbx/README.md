# OpenDBX

OpenDBX is a database abstraction layer: applications program against one
stable C API (`libopendbx`) or C++ API (`libopendbxplus`) while backend
driver modules translate to native client libraries (MySQL, PostgreSQL,
SQLite 2/3, Firebird, MS SQL, Sybase, Oracle, ODBC).

## OHOS 适配

- **核心库优先**：`--with-backends=`（空列表）只构建与后端无关的
  `libopendbx` + `libopendbxplus`；每个后端都需要 OHOS 上没有的厂商
  客户端库，核心库除 `libdl` 外零依赖。
- **裁剪 UTILS/NLS**：`--disable-utils` 去掉 `odbx-sql` 工具及其
  readline/ncurses 依赖链；`--disable-nls` 去掉 libintl 依赖。
- **C++ 标准**：源码早于 C++11（含动态异常声明），与 Gentoo/Alpine
  一致使用 `-std=c++14` 编译。
- **上游测试**：`test/odbxtest.sh` 回归套件需要真实数据库服务器与
  `odbxtest.site` 凭证（Gentoo 同样将其标记为交互式受限），OHOS 上
  不可执行；API 契约由 `test_package/` 的两个消费者测试覆盖。
- **并行限制**：`make -j1`（上游不支持并行构建，Gentoo bug #322221）。

## 依赖关系

- 编译依赖：无（除系统 `libdl` 外）。
- 运行依赖：无（后端 `.so` 由 `dlopen` 在运行时按需加载，本配方不打包）。

## 参考资料

- 官网：https://www.linuxnetworks.de/doc/index.php/OpenDBX
- 源码：https://www.linuxnetworks.de/opendbx/download/opendbx-1.4.6.tar.gz
- 打包参考：Gentoo `dev-db/opendbx`、Alpine `community/opendbx`
