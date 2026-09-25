# DRAFT-libdsme-0.67.0-ohos-abstract-af-unix-socket

## 现象

libdsme 0.67.0 的上游测试（Check）在 OHOS 上依次遇到：

```
tests/ut_libdsme.c: daemon_start: E: MOCK: unlink(/tmp/ut_libdsme.sock) failed: Read-only file system
tests/ut_libdsme.c: daemon_start: E: MOCK: bind(.../ut_libdsme.sock) failed: Operation not permitted
```

探测结论（设备实测）：

| 路径 | bind() 结果 |
|------|-------------|
| `/tmp/ohc-probe.sock` | EROFS（只读挂载） |
| `$HOME/*.sock`（HMDFS） | EPERM（Operation not permitted） |
| `/dev/shm/*.sock` | EACCES |
| `\0abstract-name`（抽象命名空间） | **成功（bind+connect 均可用）** |

## 根因

OHOS 用户态没有可写的、允许创建 AF_UNIX 文件系统套接字的目录：/tmp 只读，
HMDFS 全域被策略拒绝，/dev/shm 无权限。Linux 抽象套接字不占用文件系统路径，
是唯一可行方案，但需要调用方配合（sun_path[0]='\0' 且 connect/bind 长度按
抽象命名空间计算），标准 socket API 的"路径"约定无法表达首字节 NUL。

## 修复

库侧约定 `@` 前缀 = 抽象套接字（与 systemd 相同惯例）：

```c
if (dsmesock_filename[0] == '@') {
    size_t name_len = strlen(dsmesock_filename + 1);
    memcpy(c_addr.sun_path + 1, dsmesock_filename + 1, name_len);
    addrlen = (socklen_t)(offsetof(struct sockaddr_un, sun_path) + 1 + name_len);
} else {
    strcpy(c_addr.sun_path, dsmesock_filename);
    addrlen = sizeof(c_addr);
}
connect(fd, (struct sockaddr *)&c_addr, addrlen);
```

测试侧：mock daemon 绑定 `@ut_libdsme`，抽象名下跳过 unlink/chmod。

## 验证

- libdsme 上游测试：2/2（`100%: Checks: 2, Failures: 0, Errors: 0`）
- 消费者测试：抽象套接字往返 + 负向控制（不存在的端点返回 NULL）通过
- 普通文件系统路径行为不变（Linux 兼容）

## 适用范围

任何 OHOS 上的 AF_UNIX 使用者（D-Bus、DSME、自定义 IPC）及以 /tmp 套接字
为夹具的上游测试。
