# IPC::ShareLite

## 简介

IPC::ShareLite 是一个 Perl 模块，提供轻量级的 System V 共享内存段访问接口。它封装了 SysV IPC 共享内存和信号量，简化了多进程间数据共享的实现。

## 功能概述

- **共享内存管理**：创建、读取、写入、销毁共享内存段
- **信号量锁**：自动管理共享内存的读写锁（互斥锁和共享锁）
- **简单 API**：提供 `new()`, `store()`, `retrieve()`, `destroy()` 等简洁方法
- **跨进程共享**：支持多进程间高效数据交换

## OHOS 适配要点

### 编译适配

| 问题 | 解决方案 |
|------|----------|
| musl 头文件路径 | Makefile.PL 补丁添加 `INC => '-I~/usr/local/include'` |
| musl 库路径 | Makefile.PL 补丁添加 `LDDLFLAGS => '-shared -L~/usr/local/lib -B~/usr/local/lib/'` |
| XS 模块加载 | 受 SELinux HMDFS 限制，需管理员安装到系统目录 |

### 系统依赖

**SysV IPC 支持**：鸿蒙系统完整支持 SysV IPC
- 共享内存：shmget/shmat/shmdt/shmctl ✅
- 信号量：semget/semctl/semop ✅
- 消息队列：msgget/msgctl/msgrcv/msgsnd ✅

### 已知限制

1. **HMDFS SELinux 限制**：用户目录的 .so 文件无法加载，需管理员安装
2. **测试验证**：编译产物完整，但功能测试需管理员安装后进行

## 依赖关系

### 编译依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | 5.42.0 | Perl 运行环境 |
| musl | 1.2.5 | C 标准库（头文件和库文件） |
| clang | 18.1.8 | 编译器 |

### 运行依赖

| 依赖 | 说明 |
|------|------|
| Perl 5.x | Perl 运行环境 |
| SysV IPC | 内核共享内存和信号量支持 |

## 参考资料

- [CPAN - IPC::ShareLite](https://metacpan.org/pod/IPC::ShareLite)
- [SysV IPC 文档](https://man7.org/linux/man-pages/man7/sysvipc.7.html)