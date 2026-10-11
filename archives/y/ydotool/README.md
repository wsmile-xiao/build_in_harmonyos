# ydotool

- 上游：https://github.com/ReimuNotMoe/ydotool
- 版本：1.0.4（tag `v1.0.4`）
- 许可证：AGPL-3.0-or-later
- 构建系统：CMake（`project(ydotool C)`，C99，无第三方依赖）

## 简介

通用命令行输入自动化工具（不依赖 X/Wayland）：`ydotoold` 打开 `/dev/uinput`
建立持久虚拟输入设备，`ydotool` 客户端把 `input_event` 事件经 AF_UNIX
数据报 socket 发给守护进程。子命令：`click` / `key` / `mousemove` / `type`。

## HarmonyOS PC 适配要点

| 方面 | 状态 |
|------|------|
| 编译（OHOS SDK clang 15 / API 26） | 通过（`linux/uinput.h` 由 sysroot 提供，零源码 API 改动） |
| 版本号输出 | 补丁 0001：`-DYDOTOOL_VERSION` + 回退（归档无 git 元数据） |
| man 页 | 补丁 0002：scdoc 可选（本平台无 scdoc） |
| CMake 4.x 策略 | 配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| `/dev/uinput` 运行时 | **平台边界**：普通用户进程 EACCES（需系统级权限），`ydotoold` 无法创建虚拟设备 |
| AF_UNIX socket | **平台边界（E024）**：SELinux 禁止路径名 Unix socket `bind()`（EPERM）；daemon/client 通道需允许该操作的执行域 |
| socket 路径 | 默认 `/tmp/.ydotool_socket` 不可用（/tmp 只读）；用 `-p`/`XDG_RUNTIME_DIR` 指定可写路径 |
| 消费者测试 | `test_package/test.sh` 16 条断言（线协议逐字节 + CLI 契约 + 平台边界） |

## 使用（设备侧）

```sh
# 守护进程（需对 /dev/uinput 有写权限；普通用户进程在 OHOS 上会被拒绝）
ydotoold -p "$TMPDIR/.ydotool_socket" &
# 客户端
YDOTOOL_SOCKET="$TMPDIR/.ydotool_socket" ydotool key 28:1 28:0
```

## 归档

| 版本 | 状态 | 测试 |
|------|------|------|
| 1.0.4 | built | 上游 0；消费者测试设计 16 条（OHOS E024 环境执行 9/9 通过 + 7 条线协议断言平台受限跳过；允许 AF_UNIX 的环境 16/16） |
