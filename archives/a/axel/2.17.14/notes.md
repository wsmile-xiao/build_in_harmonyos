# axel 2.17.14 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：`ohc-run.py init-build axel 2.17.14`
2. 应用补丁：4 个补丁（config.guess, config.sub, compat-android.h, configure umask）
3. 配置：`bash ./configure --prefix=/storage/Users/currentUser/usr/local SSL_CFLAGS=... SSL_LIBS=...`
4. 编译：`make -j1`
5. 安装（staging）：`make install DESTDIR=$TEST_PREFIX`
6. 安装（本地）：`make install`
7. 验证：`axel --version` → `Axel 2.17.14 (linux-ohos)`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_cancel 等函数未定义 | musl/OHOS 不支持 pthread_cancel | 扩展 compat-android.h 条件，在 __OHOS__ 时启用替代实现 |
| 2 | PTHREAD_CANCEL_* 宏冲突 | OHOS pthread.h 已定义这些宏，与 enum 冲突 | 移除 enum 定义，使用 OHOS 已有的宏定义 |
| 3 | config.status Permission denied | HMDFS + umask 077 导致临时目录权限不足 | 修改 configure 中 umask 077→022 |
| 4 | OpenSSL not found | 系统未安装 OpenSSL | 使用 Conan 制品仓 openssl/1.1.1w |

## 源码修改

### compat-android.h (0003)
- 扩展条件判断：`#if defined(__ANDROID__) || defined(__OHOS__)`
- 添加 pthread_cancel、pthread_setcancelstate、pthread_setcanceltype 的替代实现
- 移除 PTHREAD_CANCEL_* enum 定义（OHOS 已有宏定义）

### build-aux/config.guess (0001) & config.sub (0002)
- 标准 OHOS 三元组补丁（E007/E072）

### configure (0004)
- umask 077→022 修复 HMDFS 权限问题
- HMDFS 文件系统下，umask 077 创建的目录权限为 700，但文件 owner (20001006) 与当前用户 (20020101) 不匹配，导致 Permission denied

## 依赖版本

- openssl: 1.1.1w（Conan 制品仓 ohpcd）

## 验证结果

```bash
$ axel --version
Axel 2.17.14 (linux-ohos)

Copyright 2001-2007 Wilmer van der Gaast,
      2007-2009 Giridhar Appaji Nag,
      2008-2010 Philipp Hagemeister,
```

## 知识发现

**HMDFS umask 077 权限问题**：
- HMDFS (Huawei Mobile Distributed File System) 下所有文件 owner 为 uid 20001006 (file_manager)
- 当前用户 uid 为 20020101，与文件 owner 不匹配
- umask 077 创建的目录权限为 700（仅 owner 可访问），导致当前用户无法写入
- umask 022 创建的目录权限为 755，当前用户可通过 "others" 权限访问
- 解决方案：修改 configure 脚本中 umask 077→022

**musl pthread_cancel 兼容性模式**：
- axel 项目已有 Android 兼容层（compat-android.h），提供 pthread_cancel 替代实现
- OHOS 与 Android 类似，都基于 musl，不支持 pthread_cancel
- 但 OHOS 的 pthread.h 已定义 PTHREAD_CANCEL_* 宏，需避免重复定义
- 解决方案：扩展兼容层条件到 __OHOS__，移除 enum 定义
---

**编译结束**: 2026-08-05 08:08
**最终状态**: built
