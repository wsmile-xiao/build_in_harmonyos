# sysrepo

[sysrepo](https://github.com/sysrepo/sysrepo) 是一个基于 YANG 的配置与运行状态数据存储（datastore），提供 NETCONF 风格的 API，供应用程序与守护进程进行配置管理、订阅通知与操作数据查询。常与 [libyang](https://github.com/CESNET/libyang)（YANG/YIN 解析与数据操作库）配套使用。

- 上游版本：v3.7.11（GitHub tag）
- 许可证：BSD-3-Clause
- 构建系统：CMake
- 依赖：libyang/3.13.6（本仓归档）；测试依赖 cmocka/2.0.2

## 本仓适配版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 3.7.11 | built | 见 `3.7.11/notes.md`：库本体（连接/会话/数据存储读写/模块管理）可用；订阅事件管道依赖 mkfifo，在 OHOS 沙箱上不可用（平台缺口，已如实记录） |

## OHOS 适配要点（详见 3.7.11/notes.md）

- robust mutex 缺失 → 条件编译降级（`SR_NO_ROBUST_MUTEX`）
- 动态加载器要求 .so 有效签名 → package 内签名
- `/dev/shm` 只写虚拟目录 → `SYSREPO_SHM_DIR` 指向可列目录
- 应用 UID 无 passwd 条目 → `SR_NO_PASSWD_ENTRIES` 合成 `uid<N>` 映射
