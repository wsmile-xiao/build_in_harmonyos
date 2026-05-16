# userspace-rcu 0.15.6 Release Note

## 版本信息
- **软件名称**: userspace-rcu
- **版本号**: 0.15.6
- **发布日期**: 2025-10-21 (上游)
- **编译日期**: 2026-05-08
- **License**: LGPL-2.1-or-later AND MIT

## HongMeng 平台编译说明

### 编译状态
**Partial (部分成功)** - 编译和测试完成，但使用了 out-of-tree 构建模式规避 HMDFS 文件系统限制

### 关键变更
1. **补丁**: patches/0001-fix-tmpdir-for-hmdfs.patch
   - 修复 autotools 在 HMDFS 上创建临时目录的权限问题
   - 将 `umask 077` 改为 `umask 002`
   - 使用 `.config-tmp` 子目录

2. **构建模式**: Out-of-tree 构建 (构建目录: ~/tmp/userspace-rcu-build)

### 测试结果
```
Testsuite summary for userspace-rcu 0.15.6
============================================================================
# TOTAL: 636
# PASS:  632
# SKIP:  4
# FAIL:  0
# ERROR: 0
============================================================================
```

跳过的测试为 Linux 特定的 sysfs 测试，不影响 HongMeng 平台使用。

## 安装产物清单

### 动态库 (lib/)
- liburcu.so.8.1.0 → liburcu.so.8 → liburcu.so
- liburcu-bp.so.8.1.0
- liburcu-cds.so.8.1.0
- liburcu-common.so.8.1.0
- liburcu-mb.so.8.1.0
- liburcu-memb.so.8.1.0
- liburcu-qsbr.so.8.1.0

### 静态库 (lib/)
上述所有库的 .a 版本

### 头文件 (include/urcu/)
- urcu.h, urcu-bp.h, urcu-cds.h
- urcu-mb.h, urcu-memb.h, urcu-qsbr.h
- config.h (平台配置)

### pkg-config 文件 (lib/pkgconfig/)
- liburcu.pc, liburcu-bp.pc, liburcu-cds.pc
- liburcu-mb.pc, liburcu-memb.pc, liburcu-qsbr.pc

## 平台适配说明

### 支持的功能
- ✅ atomic builtins (Clang 支持)
- ✅ pthread 线程同步
- ✅ clock_gettime
- ✅ sched_getcpu
- ✅ sched_setaffinity
- ✅ fork/vfork
- ✅ mmap

### 不支持的功能 (已 SKIP 测试)
- sysfs CPU mask 解析 (Linux 特定)

## 已知限制

### HMDFS 文件系统
- autotools configure 脚本无法在源码目录直接创建临时目录
- 原因: `mktemp -d "./confXXXXXX"` 使用 `umask 077` 导致权限问题
- 影响: 无法使用 ohc-run.py 的标准流程完成 package/finish 步骤

### 解决方案
使用 out-of-tree 构建模式，详见 PROGRESS.md

## 后续版本编译建议
1. 所有 autotools 软件包建议使用 out-of-tree 构建
2. 将 HMDFS-autotools-tmpdir 问题沉淀为 L1 平台真理知识
3. 建议技能维护者增加对 HMDFS 的特殊处理支持