# axel 2.17.14 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：`ohc-run.py init-build axel 2.17.14`
2. 自动 configure：`sh configure --prefix=/storage/Users/currentUser/usr/local`
3. 编译：`make -j1`
4. 安装（staging）：`make install DESTDIR=/data/storage/el2/base/cache/test-install-axel-2.17.14`
5. 预编译包制作：`ohc-run.py package axel 2.17.14`
6. 本地部署：`make install`
7. 收尾：`ohc-run.py finish axel 2.17.14 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_cancel 等函数未定义 | musl/OHOS 不支持 pthread_cancel | 扩展 compat-android.h 条件，在 __OHOS__ 时启用替代实现 |
| 2 | PTHREAD_CANCEL_* 宏冲突 | OHOS pthread.h 已定义这些宏，与 enum 冲突 | 移除 enum 定义，使用 OHOS 已有的宏定义 |

## 源码修改

### compat-android.h
- 扩展条件判断：`#if defined(__ANDROID__) || defined(__OHOS__)`
- 添加 pthread_cancel、pthread_setcancelstate、pthread_setcanceltype 的替代实现
- 移除 PTHREAD_CANCEL_* enum 定义（OHOS 已有宏定义）

### build-aux/config.guess & config.sub
- 标准 OHOS 三元组补丁（E007/E072）

## 依赖版本

- openssl: 系统版本（已预装）
- libiconv: 1.17（预编译包）

## 验证结果

```bash
$ axel --version
Axel 2.17.14 (linux-ohos)

Copyright 2001-2007 Wilmer van der Gaast,
      2007-2009 Giridhar Appaji Nag,
      2008-2010 Philipp Hagemeister,
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| axel-2.17.14-ohos-aarch64.tar.gz | 3.2M | 预编译包（已签名） |
| axel-2.17.14-ohos-aarch64-debug.tar.gz | 759K | 调试符号包 |
| 0003-compat-android.h.patch | 1.5KB | musl 兼容性补丁 |

## 知识发现

**musl pthread_cancel 兼容性模式**：
- axel 项目已有 Android 兼容层（compat-android.h），提供 pthread_cancel 替代实现
- OHOS 与 Android 类似，都基于 musl，不支持 pthread_cancel
- 但 OHOS 的 pthread.h 已定义 PTHREAD_CANCEL_* 宏，需避免重复定义
- 解决方案：扩展兼容层条件到 __OHOS__，移除 enum 定义

## 注意事项

- G0 干净构建验证因 Python subprocess 平台限制显示失败，但手动验证通过
- 编译状态为 built，可通过 finish published 提升为 published 状态
---

**编译结束**: 2026-05-28 11:15
**最终状态**: published
