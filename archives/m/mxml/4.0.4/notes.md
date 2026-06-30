# mxml 4.0.4 编译笔记

## 编译概述

**软件**: Mini-XML (mxml) 4.0.4
**日期**: 2026-06-08
**状态**: published
**构建系统**: autotools

## 遇到的问题与解决方案

### 1. E007: config.guess 无法识别 HarmonyOS 系统

**问题表现**:
```
configure: error: cannot guess build type; you must specify one
```

**根本原因**: GNU config.guess 脚本不包含 HarmonyOS/__OHOS__ 检测分支

**解决方案**: 使用 patch-autotools-ohos.pl 脚本自动打补丁
- 添加 __OHOS__ LIBC 检测
- 添加 HarmonyOS 系统识别 case 分支
- 输出标准三元组 aarch64-unknown-linux-ohos

### 2. E072: config.sub 三元组验证失败

**问题表现**:
```
Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'
```

**根本原因**: config.sub 未识别 ohos 作为合法操作系统值

**解决方案**: 手动修改 config.sub
- 在 kernel-os 白名单（case $kernel-$os-$obj in）中添加 `linux-ohos*-`
- 在 OS 白名单（case $os in）中添加 `ohos*`

### 3. E011: HMDFS 文件系统 umask 077 权限问题

**问题表现**:
```
config.status[714]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根本原因**: HMDFS 文件系统的 UID 映射机制导致 umask 077 创建的临时目录无法被当前进程写入

**解决方案**: 修改 configure 脚本中 `umask 077` 为 `umask 000`

## 编译过程记录

### Phase 1: 初始化 (init-build)
- ✅ 源码下载: 使用 codeload.github.com 镜像
- ✅ 解压: mxml-4.0.4.tar.gz
- ✅ 骨架创建: archives/m/mxml/4.0.4/

### Phase 2: 编译 (configure + make)
- ✅ 应用补丁: config.guess, config.sub, configure
- ✅ configure: --prefix=/storage/Users/currentUser/usr/local
- ✅ make: -j1
- ✅ make test: 3个测试全部通过

### Phase 3: 安装与验证
- ✅ make install DESTDIR: staging 验证通过
- ✅ make install: 本地安装到 ~/usr/local
- ✅ pkg-config 验证: mxml4 4.0.4 正常

### Phase 4: 打包
- ✅ 预编译包生成: mxml-4.0.4-ohos-aarch64.tar.gz (1.9MB)
- ✅ 调试包生成: mxml-4.0.4-ohos-aarch64-debug.tar.gz (212KB)
- ✅ ELF 签名: 完成

## 测试结果

```
Testing library...
Stdio file test passed!
String test passed!
File descriptor test passed!
```

## 安装产物

**静态库**: lib/libmxml4.a (190KB)
**动态库**: lib/libmxml4.so.2 (126KB)
**头文件**: include/libmxml4/mxml.h
**pkg-config**: lib/pkgconfig/mxml4.pc

## 知识沉淀

本次编译遇到的 3 个问题均为平台级问题（L1 级知识），已记录到知识图谱：
- E007: config.guess HarmonyOS 识别
- E072: config.sub 三元组验证
- E011: HMDFS umask 权限限制

## 补丁文件说明

**0001-config.guess.patch**: 平台适配补丁
**0002-config.sub.patch**: 平台适配补丁
**0003-configure.patch**: 平台适配补丁

所有补丁均为 platform_only 类型，仅适用于 HarmonyOS 平台。

---

**编译结束**: 2026-06-08 11:42
**最终状态**: published