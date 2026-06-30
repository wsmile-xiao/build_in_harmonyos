# radare2 6.0.7 编译笔记

## 编译环境

- 构建系统: autotools
- 平台: OpenHarmony / HarmonyOS
- 架构: aarch64
- 编译器: clang 15.0.7

## 编译过程

### 初始化

- 源码位置: ~/tmp/builds/radare2-6.0.7.work/radare2-6.0.7
- 构建系统: autotools
- configure 参数: --prefix=$DEFAULT_PREFIX --without-qjs WANT_QJS=0 USERCC=clang HOST_CC=clang

### 问题与解决方案

#### 问题 1: pthread_cancel 不支持

- **现象**: 编译失败于链接阶段，pthread_cancel 函数在 HarmonyOS 平台不支持
- **位置**: libr/util/thread.c 第232行
- **解决方案**: 将 `#ifdef __ANDROID__` 改为 `#if defined(__ANDROID__) || defined(__OHOS__) || defined(__HARMONYOS__)`，使用 pthread_kill(tid, 9) 替代 pthread_cancel
- **补丁**: 0001-pthread_cancel-harmonyos.patch

#### 问题 2: HOST_CC 未设置导致编译器为 'c'

- **现象**: shlr/Makefile 中 HOST_CC 未正确设置，导致 sdb 编译时使用 'c' 作为编译器
- **原因**: shlr/Makefile 中检查 gcc 是否可用，但 HarmonyOS 中 gcc 不存在
- **解决方案**: 修改 shlr/Makefile，先检查 clang 是否可用
- **补丁**: 0002-host-cc-clang.patch

#### 问题 3: subprojects/sdb/config.mk 中 CC 默认为 gcc

- **现象**: subprojects/sdb/config.mk 中 CC?=gcc，但 gcc 不存在
- **解决方案**: 将 CC?=gcc 改为 CC?=clang
- **补丁**: 0003-sdb-cc-clang.patch

## 知识提取记录

### E081: pthread_cancel 在 HarmonyOS 不支持

- **错误类型**: 系统调用缺失
- **平台**: HarmonyOS
- **症状**: 链接阶段失败，undefined reference to pthread_cancel
- **解决方案**: 使用 pthread_kill(tid, 9) 替代，需要添加 __OHOS__ 或 __HARMONYOS__ 条件编译
- **相关文件**: libr/util/thread.c
- **提交状态**: 草稿（待合并）

### HOST_CC 编译器设置

- **错误类型**: 构建工具缺失
- **平台**: HarmonyOS
- **症状**: 编译命令为 'c' 而不是 clang
- **原因**: Makefile 中检查 gcc 是否可用，但 gcc 不存在
- **解决方案**: 修改 Makefile，先检查 clang 是否可用
- **相关文件**: shlr/Makefile, subprojects/sdb/config.mk

## 最终状态

- 编译状态: built
- 版本验证: radare2 6.0.7
- 质量门禁: PASS (G0-G4)
- 预编译包: radare2-6.0.7-ohos-aarch64.tar.gz (93MB)
- 补丁文件: 3 个---

**编译结束**: 2026-05-20 20:36
**最终状态**: built
---

**编译结束**: 2026-05-20 20:37
**最终状态**: built
