# NcFTP 3.3.0-r0 编译笔记

## 编译信息
- 软件名: ncftp
- 版本: 3.3.0-r0
- 来源: Alpine Linux (实际从官网下载)
- 描述: A set of free application programs implementing FTP
- 编译日期: 2026-05-27

## 编译过程

### 1. 源码获取
从官网下载: https://www.ncftp.com/public_ftp/ncftp/ncftp-3.3.0-src.tar.gz

### 2. Configure
使用标准 configure:
```bash
./configure --prefix=/storage/Users/currentUser/usr/local
```

configure 检测到:
- 平台: harmonyos
- 编译器: clang
- curses 库: ncursesw

### 3. Make
编译过程中遇到 TMPDIR 问题:
- 问题: clang 在 /tmp 创建临时文件被拒绝（只读文件系统）
- 解决: 设置 TMPDIR=/data/storage/el2/base/cache
- 部分: 手动编译 ncftpbookmarks 等工具，使用 -Wl,-rpath 选项

### 4. Install
手动安装到 staging 目录

### 5. ELF 签名
使用 ohc-run.py sign-elf 签名所有二进制文件

## 编译产物
- ncftp (268KB)
- ncftpbatch (236KB)
- ncftpbookmarks (388KB)
- ncftpget (215KB)
- ncftpls (191KB)
- ncftpput (220KB)

## 验证
- ncftp --version: 显示版本信息 NcFTP 3.3.0-r0

## 注意事项
1. TMPDIR 必须设置为 /data/storage/el2/base/cache（/tmp 只读）
2. 所有二进制文件需要 ELF 签名才能在鸿蒙系统上执行
3. ncftpbookmarks 编译需要正确的 NCFTPPATH 宏定义（必须加引号）

## 知识发现
- E052: TMPDIR 问题 - clang 默认使用 /tmp，但在鸿蒙系统上 /tmp 只读，必须设置 TMPDIR 环境变量
---

**编译结束**: 2026-08-07 04:52
**最终状态**: built
