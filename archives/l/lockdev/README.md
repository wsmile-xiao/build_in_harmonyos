# lockdev

## 简介

lockdev 是一个设备锁定库，提供了一种稳定的方式来锁定 Unix/Linux 系统上的设备。它支持 FSSTND 1.2 和 SVr4 设备锁定方法，设计为可移植且避免与其他程序冲突。

## 功能

- 设备锁定测试（`dev_testlock`）
- 设备锁定（`dev_lock`）
- 设备重新锁定（`dev_relock`）
- 设备解锁（`dev_unlock`）

## 作者

- Fabrizio Polacco <fab@prosa.it> (原作者，1997, 1999)
- Gergely Nagy <algernon@debian.org> (维护者，自 1.0.1 起)

## 编译版本

- **版本**: 1.0.3
- **构建系统**: Makefile
- **编译器**: clang
- **状态**: built

## 鸿蒙适配

### 补丁列表

1. **0001-Makefile.patch**: 添加 DESTDIR 支持，修改 CC 为 clang
2. **0002-src-lockdev.c.patch**: 添加非 GNU 平台支持，定义 MAJOR/MINOR 宏

### 编译选项

```bash
make basedir=$HOME/usr/local shared static
make basedir=$HOME/usr/local DESTDIR=$TEST_PREFIX install
```

## 安装产物

- 静态库: liblockdev.a
- 共享库: liblockdev.so.1.0.3
- 头文件: lockdev.h, ttylock.h
- 手册: lockdev.3

## 许可证

LGPL 2.1