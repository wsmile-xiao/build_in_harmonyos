# DRAFT: OHOS 沙箱下 dbus-daemon 会话总线运行能力补齐

- **草稿 ID**: `DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime`
- **来源**: dbus 1.14.10.1 适配 fix 轮次（r01/r02 真实日志，任务 pc1-13，PR #9419）
- **状态**: DRAFT（随 dbus PR #9419 同仓交付，待主编/AI 审核提升为 E 条目）
- **配套文件**: `knowledge/drafts/DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime.kv`（同 stem 配对）

## 问题现象

OHOS 沙箱环境下 dbus-daemon 会话总线无法启动/认证，典型错误序列：

```
dbus[PID]: Could not get password database information for UID of current process: User "???" unknown
dbus[PID]: Failed to start message bus: Memory allocation failure in message bus
dbus-daemon[PID]: Failed to start message bus: Failed to bind socket "/tmp/dbus-XXXX": Read-only file system
dbus-daemon[PID]: Failed to start message bus: Failed to bind socket "...": Operation not permitted
dbus[PID]: Client authorized as UID 18446744073709551615 but our UID is 20020101, disconnecting
Error org.freedesktop.DBus.Error.AccessDenied: Client tried to send a message other than Hello without being registered
```

## 根因

1. **AF_UNIX bind 被禁止**：OHOS PC 用户沙箱对 AF_UNIX 文件 socket `bind()` 返回 `EPERM`；`/tmp` 为 erofs 只读（`EROFS`），HMDFS 用户目录 bind 也返回 `EACCES/EPERM`（与 E461 同根因的能力矩阵）。
2. **musl 用户数据库缺失**：OHOS 用户空间 musl libc 的 `getpwuid_r/getpwnam_r` 直接解析只读 `/etc/passwd`，运行 UID（如 20020101）无记录 → `init_system_db()` 失败。
3. **TCP 无对端凭证**：`SO_PEERCRED` 仅对 AF_UNIX 有效；TCP 下服务端拿不到对端 UID（显示 18446744073709551615 = -1），默认 `auth_via_default_rules` 按 UID 匹配校验断开。

## 方案

1. **TCP 等价会话总线**：`<listen>tcp:host=127.0.0.1,port=0</listen>` + `<auth>ANONYMOUS</auth>` + `<allow_anonymous/>`，`dbus-daemon --print-address --nofork` 输出地址。
2. **环境恢复**：为运行 UID 提供 `getpwuid_r/getpwnam_r` 兼容条目（passwd shim，仅环境恢复，不改被测代码/配置；生产恢复条件=设备具备 AF_UNIX 权限且用户有 passwd 记录）。
3. **消费方自动 Hello**：用 `dbus_bus_register()`（自动 Hello）后完成 `org.freedesktop.DBus Peer.Ping` 往返（method return 即 PASS）；直接发消息不 Hello 会收到 AccessDenied。
4. **test_package 自启动**：测试阶段自启动包内 dbus-daemon（TCP 配置），解析 `--print-address` 注入 `DBUS_SESSION_BUS_ADDRESS` 后运行消费方测试并清理 daemon —— 该模式可迁移至其他 D-Bus 消费者库（如 libdex test-dbus）。

## 验证（r01/r02 实测命令与退出码）

```bash
# 1) 会话总线启动并打印地址
dbus-daemon --config-file=session-tcp.conf --print-address --nofork
#    → tcp:host=127.0.0.1,port=44593,family=ipv4,guid=...（daemon 持续运行，exit 0）

# 2) 消费方往返（Peer.Ping）
DBUS_SESSION_BUS_ADDRESS=$ADDR dbus-send --session --print-reply \
    --dest=org.freedesktop.DBus / org.freedesktop.DBus.Peer.Ping
#    → method return ... reply_serial=2（exit 0）

# 3) dbus-run-session 会话内命令
dbus-run-session --config-file=session-tcp.conf -- sh -c \
    'echo IN_SESSION=$DBUS_SESSION_BUS_ADDRESS; dbus-send --session --print-reply \
    --dest=org.freedesktop.DBus / org.freedesktop.DBus.Peer.Ping'
#    → IN_SESSION=tcp:... + method return（exit 0）

# 4) conan create test_package 内自启动 daemon 往返
#    → "dbus consumer roundtrip PASSED (method return)"，EXIT=0
```

完整证据见 `archives/d/dbus/1.14.10.1/reports/runtime-verification.md` 与 `test-ledger.md`。

## 适用边界

- **适用**：无 AF_UNIX 权限、无 passwd 记录的 OHOS 沙箱运行验证；D-Bus 会话总线消费者往返验证；test_package 自启动 daemon 模式迁移。
- **反例**：真实 OHOS 桌面设备（具备 AF_UNIX 与用户记录）直接 `unix:tmpdir` + EXTERNAL，无需 TCP/allow_anonymous；abstract namespace（E461 推荐）适合临时工具，不适合需稳定寻址的 dbus-daemon 会话监听。

## 恢复条件

- 目标设备具备 AF_UNIX bind 权限时：session.conf 恢复 `<listen>unix:tmpdir=${DBUS_SESSION_SOCKET_DIR}</listen>` + EXTERNAL 认证，原样运行。
- 为运行用户建立 `/etc/passwd` 记录（或 NSS 用户数据库条目）后可去除 passwd shim。

## 四范围多轴查重（2026-09-10 复核）

| 查重范围 | 结果 |
|---|---|
| knowledge/doc | E461（OHOS AF_UNIX bind EPERM 能力矩阵/abstract+tmpdir 回退）根因重叠；E086（musl 无 struct ucred/SO_PEERCRED）、E338（getpwuid 为 NULL 回退）局部覆盖 |
| knowledge/graph | 无本组合方案条目 |
| knowledge/drafts | DRAFT-ohos-dbus1-pc-alias（.pc 别名）不同主题；无本组合 |
| index.tsv | 无 |

| 七轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | partial（E461 同根因：OHOS 拒绝 AF_UNIX 文件 socket bind） |
| trigger_overlap | true（Failed to bind socket /tmp/dbus-*: Read-only file system / Operation not permitted） |
| solution_overlap | partial（E461 推荐 abstract socket；本条目为固定会话总线场景的 TCP 等价 + 认证降级） |
| combination_novelty | true（dbus-daemon 固定监听场景 TCP+allow_anonymous+passwd shim 组合无既有条目） |
| boundary_novelty | true（仅无 AF_UNIX 权限/无 passwd 记录的运行验证环境适用；生产设备直接 unix:tmpdir+EXTERNAL） |
| test_migration_novelty | true（test_package 自启动 dbus-daemon 完成真实 Peer.Ping 往返模式可迁移至其他 D-Bus 消费者库） |

**与 E461 关系**：E461 已覆盖"OHOS 不 bind AF_UNIX 文件 socket"的根因与能力矩阵、abstract namespace 回退（已覆盖部分，reuse_existing）；本轮新增部分 = dbus-daemon 固定会话监听场景的 TCP 等价路径 + allow_anonymous 认证降级 + musl passwd shim 环境恢复 + test_package 自启动往返模式（new_draft）。

**关系字段**：similar_to=E461, E086, E338；caused_by=OHOS 沙箱能力矩阵（与 E461 同根因链）；prerequisite_of=libdex test-dbus 消费者验证（后续 follow-up）；conflicts_with=无。
