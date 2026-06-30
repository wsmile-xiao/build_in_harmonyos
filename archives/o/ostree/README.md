# ostree

Operating system and container binary deployment and upgrades.

## 项目信息

- **名称**: ostree
- **官网**: https://ostreedev.github.io/ostree/
- **源码**: https://github.com/ostreedev/ostree
- **许可证**: LGPLv2+
- **编程语言**: C
- **构建系统**: autotools

## 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2026.1 | ❌ failed | 2026-05-27 | 源码下载失败（网络访问受限） |

## 功能描述

ostree是操作系统和容器的原子化部署与升级工具，提供类似git的文件系统树管理机制。

**核心特性**：
- 系统的事务性升级和回滚
- 通过HTTP增量复制内容（支持GPG签名和TLS）
- 支持并行安装多个可引导根
- 服务器和客户端二进制历史记录
- 用于构建和部署系统的内省共享库API

**应用场景**：
- Fedora CoreOS、Silverblue
- IoT设备、嵌入式系统
- Flatpak应用分发
- 汽车嵌入式系统（Torizon OS）
- 系统OTA更新

## 编译注意事项

### 依赖要求

**核心依赖（必需）**：
- glib >= 2.66.0
- liblzma >= 5.0.5（xz压缩）
- zlib
- e2p（ext2/3/4文件系统工具库）
- bison（构建工具）

**可选依赖**：
- libcurl >= 7.29.0（HTTP下载）
- gpgme >= 1.8.0（GPG签名验证）
- openssl >= 1.0.1（加密校验）
- libarchive >= 2.8.0（tar解析）
- libselinux >= 2.1.13（SELinux支持）
- libsystemd（systemd集成）
- fuse3/fuse（rofiles-fuse工具）

### OpenHarmony适配配置

**推荐最小配置**：
```bash
./configure --prefix=/usr \
    --with-curl \
    --without-soup \
    --without-soup3 \
    --without-gpgme \
    --without-libarchive \
    --without-selinux \
    --without-avahi \
    --without-libmount \
    --without-libsystemd \
    --disable-rofiles-fuse \
    --with-crypto=glib
```

**禁用的功能**：
- systemd集成（OpenHarmony不使用systemd）
- SELinux支持（OpenHarmony使用其他安全机制）
- libmount（Linux特有挂载管理）
- rofiles-fuse（需要fuse支持）

### 平台兼容性

✅ **适合OpenHarmony**

**优势**：
- 不依赖Linux桌面栈（GTK+、X11、GNOME）
- 核心依赖轻量且可移植（glib、liblzma、zlib）
- 已有多个嵌入式/汽车系统成功案例
- 提供原子化更新和回滚能力

**需要适配**：
- 引导加载器集成（ostree管理grub/syslinux等）
- 文件系统特性（hardlinks、extended attributes）
- Linux特有依赖（systemd、selinux、libmount）已禁用

### 编译问题

**当前阻塞**：
- 源码下载失败：GitHub访问受限（SSL证书+网络问题）
- 国内镜像站未收录ostree源码包

**解决方案**：
1. 用户手动下载源码包并放置到本地
2. 配置网络代理/VPN
3. 从私有仓库或内部镜像获取

## 版本历史

| 版本 | 发布时间 | 主要变更 |
|------|----------|----------|
| 2026.1 | 2026-04-10 | 最新稳定版 |
| 2025.2 | 2025-06 | 前版本 |
| 2024.4 | 2024-12 | composefs支持 |

## 相关链接

- [官方文档](https://ostreedev.github.io/ostree/)
- [GitHub仓库](https://github.com/ostreedev/ostree)
- [嵌入式案例](https://github.com/torizon)

## 后续建议

一旦源码可用，ostree可以成功编译，建议优先级：
- P0: 解决源码获取问题
- P1: 编译ostree最小配置
- P2: 集成到OpenHarmony系统更新框架