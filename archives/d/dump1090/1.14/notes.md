# dump1090 1.14 — 编译笔记

> 档案创建时间: 2026-05-21
> 最后更新: 2026-05-21 (当前状态: built)
> 源码来源: https://github.com/mutability/dump1090/archive/refs/tags/v1.14.tar.gz

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | dump1090 |
| 版本 | 1.14 (mutability) |
| 状态 | ✅ built |
| 构建系统 | Makefile |
| 源码路径 | /storage/Users/currentUser/builds/dump1090-1.14.work |

## 二、依赖链

dump1090 → rtl-sdr → libusb-1.0

### libusb-1.0 1.0.27 编译要点
- 需要 config.guess/config.sub 补丁识别 HarmonyOS
- 需要 `__MUSL__` 宏定义避免 sockaddr_storage 重定义
- 需要 `--disable-udev` 选项

### rtl-sdr 2.0.2 编译要点
- CMake 构建系统
- 需要 `__MUSL__` 和 pthread_cancel 替代方案
- rtl_adsb.c 中 pthread_cancel 需改为条件变量唤醒

## 三、遇到的问题及解决方案

### 问题 1: 依赖缺失
dump1090 需要 librtlsdr，后者需要 libusb-1.0。
解决方案: 先编译 libusb，再编译 rtl-sdr，最后编译 dump1090。

### 问题 2: sockaddr_storage 重定义
错误: `struct sockaddr_storage` 在 linux/socket.h 和 sys/socket.h 中重复定义。
根因: `__MUSL__` 宏未定义，sys/socket.h 中未跳过定义。
解决方案: 在编译时添加 `-D__MUSL__` 或在 config.h 中定义。

### 问题 3: pthread_cancel 未定义
错误: `undefined symbol: pthread_cancel`
根因: musl 不支持 pthread_cancel。
解决方案: 修改 rtl_adsb.c，使用条件变量唤醒代替 pthread_cancel:
```c
// 原代码: pthread_cancel(demod_thread);
// 改为:
do_exit = 1;
safe_cond_signal(&ready, &ready_m);
pthread_join(demod_thread, NULL);
```

### 问题 4: Modes 全局变量重复符号
错误: `duplicate symbol: Modes`
根因: 头文件中定义了全局变量，每个 .c 文件都包含一份副本。
解决方案:
1. 在 dump1090.h 中添加 `MODES_GLOBAL` 宏控制 extern
2. 在 dump1090.c 和 view1090.c 中定义 `MODES_GLOBAL` 为空以提供实际定义

### 问题 5: 动态链接失败
错误: `Error loading shared library libusb-1.0.so.0`
根因: RPATH 未正确设置，动态链接器找不到依赖库。
解决方案: 使用静态链接避免动态链接问题。

## 四、最终编译命令

```bash
# 编译 libusb
cd libusb-1.0.27.work
perl patch-autotools-ohos.pl config.guess config.sub
./configure --prefix=$DEFAULT_PREFIX --disable-udev CFLAGS="-D__MUSL__"
make CFLAGS="-D__MUSL__" && make install

# 编译 rtl-sdr
cd rtl-sdr-2.0.2.work/build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF
make && make install

# 编译 dump1090
cd dump1090-1.14.work
# 修改 Makefile: CC=cc, LIBS_RTL 使用静态库
make && cp dump1090 view1090 $DEFAULT_PREFIX/bin/
```

## 五、验证结果

```bash
$ dump1090 --help
-----------------------------------------------------------------------------
| dump1090 ModeS Receiver                              dump1090-mutability  |
-----------------------------------------------------------------------------
--device-index <index>   Select RTL device (default: 0)
--gain <db>              Set gain (default: max gain. Use -10 for auto-gain)
...
```

## 六、交付物

| 文件 | 路径 |
|------|------|
| dump1090 二进制 | /storage/Users/currentUser/usr/local/bin/dump1090 |
| view1090 二进制 | /storage/Users/currentUser/usr/local/bin/view1090 |
| 预编译包 | /storage/Users/currentUser/usr/local/share/dump1090-1.14-ohos-aarch64.tar.gz |

---
**编译结束**: 2026-05-21 16:35
**最终状态**: built (静态链接)
