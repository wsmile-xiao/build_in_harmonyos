# gkrellm

## 软件简介

gkrellm (GKrellM) 是一个系统监控工具。本适配仅包含 **gkrellmd**（守护进程/服务端），不含需要 GTK2/X11 的图形客户端（OHOS 无 GTK/X11 支持）。

gkrellmd 以守护进程方式运行，通过 TCP socket 向 gkrellm 客户端提供系统监控数据（CPU、内存、磁盘、网络等）。

- **主页**: https://github.com/toppk/gkrellm
- **许可证**: GPL-2.0-or-later
- **语言**: C

## 编译版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.3.11 | built | 仅 gkrellmd 守护进程 |

## 使用方式

```bash
# 启动守护进程（默认监听 19150 端口）
gkrellmd

# 后台运行
gkrellmd -d
```

## 注意事项

- 本适配仅构建 gkrellmd（server/ 子目录），不构建 GTK 图形客户端
- OHOS 的 /proc 访问受 SELinux 限制，部分监控数据可能不可用
