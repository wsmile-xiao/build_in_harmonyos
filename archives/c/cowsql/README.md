# cowsql

cowsql 是基于 raft 的嵌入式 SQL 数据库。

## 功能概述
- 嵌入式 SQL 数据库
- 基于 raft 的复制
- 高可用性

## OHOS 适配要点
- qsort_r 在 musl/OHOS 上不支持
- 需要使用 qsort wrapper

## 依赖关系
- libuv
- sqlite3
- raft

## 参考资料
- 源码: https://github.com/cowsql/cowsql
