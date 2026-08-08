# berkeley-db5

Berkeley DB 5.3.28 是一个高性能的嵌入式键/值数据库库，提供多种数据结构访问方法（Btree、Hash、Queue、Recno、Heap），支持事务、恢复和并发控制。

## 版本

- 5.3.28 (built)

## 特性

- 嵌入式数据库引擎（无需独立服务器进程）
- 多种访问方法：Btree、Hash、Queue、Recno、Heap
- 事务支持（ACID）
- 并发控制（多读者/多写者）
- 日志和恢复机制
- 复制和高可用性支持
- 加密支持（AES）

## 工具

| 工具 | 说明 |
|------|------|
| db_archive | 归档日志文件 |
| db_checkpoint | 检查点数据库 |
| db_deadlock | 死锁检测 |
| db_dump | 导出数据库内容 |
| db_hotbackup | 热备份 |
| db_load | 导入数据库 |
| db_log_verify | 日志验证 |
| db_printlog | 打印日志 |
| db_recover | 数据库恢复 |
| db_replicate | 复制管理 |
| db_stat | 统计信息 |
| db_tuner | 性能调优 |
| db_upgrade | 版本升级 |
| db_verify | 数据库验证 |

## 库文件

- libdb-5.3.so / libdb.a — 动态/静态链接库
- libdb-5.3.a — 静态库

## 头文件

- db.h — C接口头文件
- db_cxx.h — C++接口头文件