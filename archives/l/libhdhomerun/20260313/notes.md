# libhdhomerun 20260313 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libhdhomerun |
| 版本 | 20260313 |
| 上游 | https://github.com/Silicondust/libhdhomerun |
| 许可证 | LGPL-2.1 |
| 构建系统 | Makefile |
| 状态 | built |

## 构建步骤

1. 下载源码: `https://api.github.com/repos/Silicondust/libhdhomerun/tarball/20260313`
2. 应用补丁: `patches/0001-hdhomerun_sock_netlink.c.patch`
3. 编译: `make OS=Linux CC=clang -j1`
   - OS=Linux 必须显式传递，因为 HarmonyOS 的 `uname -s` 返回 "HarmonyOS" 而非 "Linux"
   - 这确保 Makefile 选择 netlink 接口检测并添加 `-lrt` 链接标志
4. 产物:
   - `libhdhomerun.so` — 共享库
   - `hdhomerun_config` — 命令行工具

## 适配修改

### 补丁 0001: hdhomerun_sock_netlink.c
- **问题**: `linux/socket.h` 和 `sys/socket.h` 都定义了 `sockaddr_storage`，导致重定义冲突
- **修复**: 在包含 `linux/netlink.h` 之前定义 `_UAPI_LINUX_SOCKET_H` 防止重复包含，并添加 `__kernel_sa_family_t` 的 typedef

### Makefile OS 检测
- **问题**: Makefile 通过 `uname -s` 检测操作系统，HarmonyOS 返回 "HarmonyOS" 不匹配任何已知平台
- **解决**: 在 conanfile.py build() 中显式传递 `OS=Linux`，使 Makefile 走 Linux 分支（netlink 接口检测 + -lrt）

## 依赖
- 无第三方依赖
- 系统库: pthread, rt

## 测试
- test_package 调用 `hdhomerun_discover_validate_device_id()` 验证 API 可用性
---

**编译结束**: 2026-07-15 21:59
**最终状态**: built
