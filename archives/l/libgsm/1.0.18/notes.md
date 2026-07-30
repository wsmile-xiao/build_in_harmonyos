# libgsm 1.0.18 编译笔记

## 编译信息
- 时间：2026-05-19
- 构建系统：传统 Makefile（无 configure）
- 编译器：clang --target=aarch64-linux-ohos
- 版本：gsm-1.0-pl18（实际版本号）

## 源码信息
- 下载 URL: http://www.quut.com/gsm/gsm-1.0.18.tar.gz
- 解压目录：gsm-1.0-pl18
- 大小：63KB

## 修改记录

### 1. Makefile 编译器适配
- 修改 CC=gcc → CC=clang
- 添加 --target=aarch64-linux-ohos 到 CCFLAGS
- 位置：第 46-47 行

### 2. DESTDIR 模式支持
- 添加 PREFIX 和 DESTDIR 变量定义
- 修改 INSTALL_ROOT 为动态路径
- 位置：第 74-77 行

### 3. HMDFS 硬链接问题（E046）
- HMDFS 文件系统不支持硬链接
- 修改 bin/untoast 和 bin/tcat 的创建规则
- 使用软链接替代：ln -s toast untoast/tcat
- 位置：第 315-322 行

### 4. 安装目录创建
- 修改 gsminstall 和 toastinstall 目标
- 添加 mkdir -p 创建安装目录
- 位置：第 333-343 行

## 遇到的问题

### 问题 1：SSL 证书验证失败
- URL: http://www.quut.com/gsm/gsm-1.0.18.tar.gz
- 解决：使用 curl -k 手动下载

### 问题 2：HMDFS 硬链接限制
- 错误：ln: cannot create hard link ... Operation not permitted
- 解决：使用软链接替代（ln -s）

### 问题 3：SELinux strip/chmod 限制
- strip: unable to copy file ... Operation not permitted
- chmod: Permission denied
- 记录为平台限制（Gotchas E046），不阻塞编译

### 问题 4：软链接路径错误
- 原始规则：ln ./bin/toast ./bin/tcat（相对路径错误）
- 解决：修改为 ln -s toast ./bin/tcat

## 编译产物
- lib/libgsm.a: 静态库（66KB）
- include/gsm.h: 头文件
- bin/toast: 命令行工具（78KB）
- bin/untoast, bin/tcat: 软链接
- share/man/man1/toast.1: 用户手册
- share/man/man3/*.3: API 手册

## 验证结果
- ✓ toast 工具可执行
- ✓ 静态库可被链接
- ✓ 头文件完整
- ✓ 软链接正确
**预编译包**: libgsm-1.0.18-ohos-aarch64.tar.gz (173KB)
**补丁**: 0001-makefile-harmonyos.patch
---

**编译结束**: 2026-07-16 00:47
**最终状态**: built
