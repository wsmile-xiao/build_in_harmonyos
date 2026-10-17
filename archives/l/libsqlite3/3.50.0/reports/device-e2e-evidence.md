# 真机消费者端到端证据 — libsqlite3 3.50.0（DAYU200）

## 执行环境

| 项 | 值 |
|---|---|
| 设备 | 润和 DAYU200-RK3568 |
| 系统 | OpenHarmony 6.0.0.47（API20，aarch64，64 位） |
| 设备序列号 | 450100445634303332018f3e7d2dba00 |
| 执行时间 | 2026-09-29T17:10:43+08:00 |
| 执行器 | `bash /mnt/d/OHDev/automation/device_runner.sh run libsqlite3_e2e ...`（上传→执行→采集退出码） |
| 二进制 | `test.c` 消费者端到端用例，经 `aarch64-unknown-linux-ohos-clang` **静态链接打包产物 `libsqlite3.a`**（Conan 包内 `include/sqlite3.h` + `lib/libsqlite3.a`） |
| x86 对照 | 同源同断言，native gcc + 与配方一致编译开关 |

## 用例与结果（真机 / x86 对照一致）

| 用例 | 内容 | 校验点 | DAYU200 真机 | x86 对照 |
|---|---|---:|---|---|
| case1 持久化 CRUD 生命周期 | 建库→建表/索引→批量插入→预编译绑定查询→事务回滚→更新→删除→关闭重开→持久性校验+`integrity_check` | 10 | 10/10 | 10/10 |
| case2 查询引擎路径 | JOIN+聚合、范围过滤、FTS5 虚表 `MATCH`、RTREE 空间查询 | 7 | 7/7 | 7/7 |
| case3 版本/编译特性契约 | `libversion`=3.50.0、`libversion_number`=3050000、`threadsafe`=1、`compile_options` 含 FTS5/RTREE/THREADSAFE | 7 | 7/7 | 7/7 |
| **合计** | | **24** | **`RESULT: 24 checks, 0 failures`（exit=0）** | **`RESULT: 24 checks, 0 failures`（exit=0）** |

建库/插入/查询回环要点：case1 在设备文件系统上创建 `e2e_consumer.db`，插入 3 行、绑定参数查询、事务回滚恢复 `qty=30`、删除后 `COUNT=2`，**关闭重开后数据与回滚状态持久**（文件库真实落盘回环），并执行 `integrity_check`。

## 证据文件

- `_device_evidence.json`（`/root/ohpc/scratch/libsqlite3_e2e/`）：`{"job":"libsqlite3_e2e","device_serial":"450100445634303332018f3e7d2dba00","system":"OpenHarmony 6.0.0.47 (API20, aarch64, 64bit)","command":"./test_sqlite3_device","exit_code":0,"timestamp":"2026-09-29T17:10:43+08:00"}`
- `x86_control_output.txt`：x86 对照完整输出（24/24）
- 设备执行完整输出：同 24 行 `ok 01..ok 24` + `RESULT: 24 checks, 0 failures`
