# p8-platform

Platform support library used by libCEC.

## 描述

p8-platform 是 Pulse-Eight 开发的跨平台支持库，为 libCEC（Consumer Electronics Control）提供平台抽象层。

## 功能

- 线程管理（mutex、atomics、condition variable）
- Socket 抽象（TCP、cdevsocket）
- 时间工具（GetTimeMs、CTimeout）
- 同步缓冲区（SyncedBuffer）
- 事件机制（CEvent）

## 编译信息

- 版本: 2.1.0.1
- 构建系统: CMake
- 编译器: OHOS SDK clang++ (v15.0.4)
- 状态: **published**

## 功能测试

**测试日期**: 2026-06-09
**测试结果**: ✅ **全部通过 (11/11)**

| 模块 | 测试项 | 结果 |
|------|--------|------|
| TimeUtils | GetTimeMs() | ✅ PASS |
| TimeUtils | CTimeout 超时机制 | ✅ PASS |
| Mutex | CMutex 基本锁操作 | ✅ PASS |
| Mutex | CMutex TryLock 可重入 | ✅ PASS |
| Mutex | CLockObject RAII | ✅ PASS |
| Event | CEvent 等待超时 | ✅ PASS |
| Event | CEvent 信号触发 | ✅ PASS |
| Event | CEvent::Sleep | ✅ PASS |
| Buffer | SyncedBuffer Push/Pop | ✅ PASS |
| Threads | 多线程同步 | ✅ PASS |
| Threads | CThread 类管理 | ✅ PASS |

详细报告: `2.1.0.1/reports/test-report.md`

## 预编译包

| 包名 | 大小 | 说明 |
|------|------|------|
| p8-platform-2.1.0.1-ohos-aarch64.tar.gz | 333KB | 生产版本 |
| p8-platform-2.1.0.1-ohos-aarch64-debug.tar.gz | 51KB | 调试版本 |

## 使用方法

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- p8-platform 2.1.0.1

# pkg-config 验证
pkg-config --modversion p8-platform
# 输出: 2.1.0

# 编译链接
pkg-config --cflags --libs p8-platform
# 输出: -I~/usr/local/include -L~/usr/local/lib -lp8-platform
```

## 依赖

- libCEC (Consumer Electronics Control library)

## 许可证

GPL-2.0 或商业许可（双许可）