# sshfs — SSH Filesystem

sshfs 是一个基于 FUSE (Filesystem in Userspace) 的 SSH 文件系统客户端，
允许用户通过 SFTP 协议挂载远程文件系统。

## 特性
- 基于 libfuse3（FUSE 3.x）实现
- 支持 SSH 密钥认证
- 支持多线程操作
- 支持缓存（读/写）
- 支持 ID 映射
- 支持 vsock

## 依赖
- libfuse/3.18.2+
- glib/2.84.0+

## 构建系统
Meson

## 许可
GPL-2.0-only
