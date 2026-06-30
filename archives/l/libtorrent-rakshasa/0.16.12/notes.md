# libtorrent-rakshasa 0.16.12 适配笔记

## 编译环境

- **系统**: HarmonyOS (OpenHarmony)
- **编译器**: clang 15.0.4
- **构建系统**: autotools
- **日期**: 2026-05-21

## 编译步骤

1. 下载源码（使用 curl -k 跳过 SSL 验证）
2. 运行 `autoreconf -ivf` 生成 configure 脚本
3. 复制 pkg.m4 到 scripts 目录
4. 设置 PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
5. 运行 configure: `./configure --prefix=$DEFAULT_PREFIX`
6. 编译: `make -j2`
7. 安装: `make install DESTDIR=$TEST_PREFIX`

## 问题与方案

### 问题1: SSL 证书验证失败
- **原因**: GitHub HTTPS 连接证书验证失败
- **解决方案**: 使用 `curl -k` 手动下载源码

### 问题2: configure 脚本不存在
- **原因**: Git 克隆的源码缺少预生成的 configure
- **解决方案**: 运行 `autoreconf -ivf` 生成

### 问题3: PKG_CHECK_MODULES 宏未展开
- **原因**: pkg.m4 文件不在正确位置
- **解决方案**: 复制 ~/usr/local/share/aclocal/pkg.m4 到 scripts/ 目录

### 问题4: pkg-config 找不到依赖库
- **原因**: PKG_CONFIG_PATH 未设置
- **解决方案**: 设置 `PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig`

## 交付物

- 静态库: libtorrent.a
- 动态库: libtorrent.so
- 头文件: torrent/*.h
- 预编译包: libtorrent-rakshasa-0.16.12-ohos-aarch64.tar.gz (15MB)

## 验证

```bash
pkg-config --modversion libtorrent
# 输出: 0.16.12
```