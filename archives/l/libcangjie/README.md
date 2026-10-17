# libcangjie

## 简介

C library implementing the Cangjie input method（仓颉输入法 C 实现），提供
字符查询、编码反查、部首查询等 API，数据库由 `data/table.txt` 构建为
`cangjie.db`。

## OHOS 适配
- 上游 Meson 构建系统（meson >= 1.3.2），运行时仅依赖 sqlite3
- 构建工具 meson/1.11.0 来自制品仓；`dependency('sqlite3')` 经 PkgConfigDeps + sqlite.pc 别名解析
- 共享库 `libcangjie.so.3.1.0` 别名链物化为实体拷贝；数据库随包安装到 `share/libcangjie/cangjie.db`
- 消费者测试经 `CANGJIE_DB` 环境变量指向包内数据库

## 依赖
- sqlite/3.53.3

## 参考
- 源码: https://gitlab.freedesktop.org/cangjie/libcangjie
- Debian 源码包: https://packages.debian.org/source/stable/libcangjie
