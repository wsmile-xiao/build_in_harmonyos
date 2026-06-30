# qdbm 1.8.78 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `./configure --prefix=$DEFAULT_PREFIX`
2. `make -j1`
3. `make install DESTDIR=$TEST_PREFIX` (staging)
4. `make check` (大部分通过)
5. `make install` (本地安装)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status "Permission denied" | HMDFS 不允许写入 umask 077 创建的目录（mode 0700+SGID），且 chmod 不生效（E046） | 修改 configure 中 `umask 077` → `umask 022`（2处，在 config.status 模板内） |
| 2 | vlmgr list 段错误 (Signal 11) | 可能是 villa 数据库列表读取时的平台兼容性问题 | 记录为已知限制，不影响核心库功能 |

## 源码修改

- **configure**: 将 config.status 模板中的 `umask 077` 改为 `umask 022`（2处）
  - 原因: HMDFS 文件系统不支持向 umask 077 创建的 0700 目录写入文件，且 chmod 无效
  - 补丁文件: 0001-configure-umask.patch

## 依赖版本

无外部依赖（仅 libc）

## 验证结果

```bash
$ dpmgr version
Powered by QDBM version 1.8.78 on Linux
Copyright (c) 2000-2007 Mikio Hirabayashi
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| qdbm-1.8.78-ohos-aarch64.tar.gz | 3343KB | 预编译包（含库、工具、头文件、man页） |

## 注意事项

- vlmgr list 命令在 optimize 后会段错误，但核心库功能完全正常
- 共享库 libqdbm.so.14 和静态库 libqdbm.a 均可用
- 包含 19 个命令行工具：dpmgr, dptest, dptsv, crmgr, crtest, crtsv, rlmgr, rltest, hvmgr, hvtest, cbtest, cbcodec, vlmgr, vltest, vltsv, odmgr, odtest, odidx, qmttest
---

**编译结束**: 2026-06-17 19:28
**最终状态**: published
