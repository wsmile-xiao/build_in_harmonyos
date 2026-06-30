# eudev

**描述**: eudev 是 systemd 项目中设备管理器 udev 的独立版本，用于管理 Linux/Unix 系统中的设备节点和设备事件。

## 项目信息

| 属性 | 值 |
|------|-----|
| 官方仓库 | https://github.com/eudev-project/eudev |
| 许可证 | GPL-2.0+ |
| 类型 | 系统工具 / 设备管理 |

## 功能特性

- 设备节点管理：自动创建、删除和管理 `/dev` 目录下的设备节点
- 设备事件处理：响应内核设备事件，执行相应的规则和动作
- 设备命名：提供持久化的设备命名方案
- 设备识别：通过多种辅助工具识别设备属性（ATA、SCSI、CDROM、V4L 等）
- 硬件数据库：维护硬件属性数据库（hwdb）

## 组件

| 组件 | 说明 |
|------|------|
| udevadm | 主命令行工具，用于查询设备信息、触发事件、控制守护进程等 |
| udevd | 设备管理守护进程 |
| libudev | 设备管理库，提供 API 供其他程序调用 |
| ata_id | ATA 设备识别工具 |
| scsi_id | SCSI 设备识别工具 |
| cdrom_id | 光驱设备识别工具 |
| v4l_id | Video4Linux 设备识别工具 |

## HarmonyOS 编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 3.2.14 | built | 2026-05-26 | 16 |

## HarmonyOS 适配要点

### 平台识别
- config.guess: 添加 `aarch64-unknown-linux-ohos` 检测
- config.sub: 添加 `linux-ohos` OS 支持

### musl libc 兼容性
- `program_invocation_short_name`: musl libc 不提供，需用宏定义替代（影响 15 个源文件）
- `get_current_dir_name()`: musl libc 不提供，需提供替代实现

### 头文件冲突
- `sockaddr_storage`: 在 `linux/socket.h` 和 `sys/socket.h` 中重复定义，需用 `__OHOS__` 宏守卫

## 使用限制

- **root 权限**: udevd 运行和设备管理功能需要 root 权限
- **设备访问**: 设备识别工具需要实际硬件设备才能完整测试
- **系统依赖**: 需要内核支持 uevent 机制

## 相关链接

- [官方文档](https://github.com/eudev-project/eudev/blob/master/README.md)
- [udev 规则语法](https://wiki.archlinux.org/title/Udev)
- [libudev API 参考](https://man7.org/linux/man-pages/dir_section_3.html)