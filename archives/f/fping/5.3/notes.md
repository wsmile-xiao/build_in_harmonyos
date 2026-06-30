# fping 5.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 源码获取：从 gitcode.com/schweikert/fping git clone v5.3 标签（Savannah/GitHub 原始下载 URL SSL 证书不可用/404）
2. 创建本地 tarball 供 init-build 使用
3. autoreconf -fi 生成 configure 脚本（源码仓库不含预生成 configure）
4. CONFIG_SHELL=bash 解决 HMDFS 权限问题
5. 修改 config.status 中 umask 077 为 umask 007（HMDFS setgid 目录需要 group 写权限）
6. ./configure --prefix=$DEFAULT_PREFIX（检测到 aarch64-unknown-linux-ohos 平台）
7. make -j1（成功编译 fping）
8. make install DESTDIR=$TEST_PREFIX（R20 DESTDIR 模式）
9. make check（无正式测试套件）
10. make install（安装到 ~/usr/local）
11. fping --version 验证成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah/GitHub 源码下载 SSL 证书失败或 404 | 平台 SSL 证书库不完整 + Savannah 原始文件 404 | 从 gitcode.com/schweikert/fping git clone v5.3 |
| 2 | aclocal/automake bad interpreter: perl 路径不存在 | 预编译 automake 的 shebang 指向 ~/usr/local/bin/perl 不存在 | ln -sf /data/service/hnp/bin/perl ~/usr/local/bin/perl + PERL5LIB 设置 |
| 3 | config.status Permission denied 创建临时文件 | HMDFS setgid 目录 + umask 077 剥夺 group 写权限 | umask 077 改为 umask 007 + CONFIG_SHELL=bash |

## 源码修改

- config.status: umask 077 → umask 007（HMDFS 兼容性修复，E002 相关）

## 依赖版本

- 无额外依赖（fping 仅依赖标准 C 库和 POSIX socket API）

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/sbin/fping --version
/storage/Users/currentUser/usr/local/sbin/fping: Version 5.3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|----------|
| fping-5.3-ohos-aarch64.tar.gz | ~72128 bytes | 预编译包 |

## 注意事项

- fping 需要 root 权限或 CAP_NET_RAW capability 才能发送 ICMP 包
- 源码从 git 仓库获取而非 release tarball，需要 autoreconf 生成 configure
- HMDFS 权限问题（E002）需要 umask 007 代替 077
---

**编译结束**: 2026-05-26 10:27
**最终状态**: published
