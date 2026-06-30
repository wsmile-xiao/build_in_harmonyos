# berkeley-db4

Berkeley DB 是一个高性能的嵌入式键/值数据库库，提供多种数据结构访问方法（Btree、Hash、Queue、Recno等），支持事务、恢复和并发控制。

## 版本

- 4.8.30 (published)

## 特性

- 嵌入式数据库引擎（无需独立服务器进程）
- 多种访问方法：Btree、Hash、Queue、Recno
- 事务支持（ACID）
- 并发控制（多读者/多写者）
- 日志和恢复机制
- SQL接口（db_sql工具）

## 工具

| 工具 | 说明 |
|------|------|
| db_archive | 归档日志文件 |
| db_checkpoint | 检查点数据库 |
| db_deadlock | 死锁检测 |
| db_dump | 导出数据库内容 |
| db_hotbackup | 热备份 |
| db_load | 导入数据库 |
| db_printlog | 打印日志 |
| db_recover | 数据库恢复 |
| db_sql | SQL接口 |
| db_stat | 统计信息 |
| db_upgrade | 版本升级 |
| db_verify | 数据库验证 |

## 库文件

- libdb-4.8.so / libdb.so — 动态链接库
- libdb-4.8.a / libdb.a — 静态链接库

## 头文件

- db.h — C接口头文件
- db_cxx.h — C++接口头文件
