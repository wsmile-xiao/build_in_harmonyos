# userspace-rcu 0.15.6

## 软件信息
- **名称**: userspace-rcu
- **版本**: 0.15.6
- **描述**: Library for userspace RCU (read-copy-update)
- **License**: LGPL-2.1-or-later AND MIT
- **源码URL**: https://lttng.org/files/urcu/userspace-rcu-0.15.6.tar.bz2
- **构建系统**: autotools

## 编译状态
- **状态**: Partial (部分成功)
- **日期**: 2026-05-08
- **平台**: aarch64-unknown-linux-gnu (HongMeng)
- **编译器**: clang 15.0.4

## 安装产物

### 库文件
- liburcu.so.8.1.0 - RCU base library
- liburcu-bp.so.8.1.0 - Bulletproof RCU
- liburcu-cds.so.8.1.0 - Concurrent Data Structures
- liburcu-common.so.8.1.0 - Common utilities
- liburcu-mb.so.8.1.0 - Memory barrier RCU
- liburcu-memb.so.8.1.0 - Memory barrier with explicit migration
- liburcu-qsbr.so.8.1.0 - Quiescent State Based Reclamation

### 静态库
所有库均提供对应的 .a 静态库版本

### 头文件
- include/urcu/*.h - RCU API 头文件
- include/urcu/config.h - 平台配置

## 测试结果
- **PASS**: 632
- **SKIP**: 4 (Linux特定sysfs测试)
- **FAIL**: 0

详见: reports/test-report.md

## 编译特殊说明

### HMDFS 文件系统限制
在 HongMeng 平台上编译时遇到 HMDFS 文件系统对 autotools 临时目录创建的特殊限制：
- `mktemp -d "./confXXXXXX"` 使用 `umask 077` 创建的目录权限过于严格
- 需要使用 out-of-tree 构建 + 修改临时目录权限

解决方案详见: patches/0001-fix-tmpdir-for-hmdfs.patch

## 依赖
无外部依赖

## 使用示例

```c
#include <urcu.h>

void reader_section() {
    urcu_read_lock();
    // 读取共享数据
    urcu_read_unlock();
}

void writer_update() {
    // 更新数据后调用 synchronize_rcu()
    synchronize_rcu();
}
```

## 文档
- [官方网站](http://liburcu.org/)
- [GitHub](https://github.com/urcu/userspace-rcu)