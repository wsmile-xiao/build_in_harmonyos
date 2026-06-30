# librtlsdr 2.0.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装依赖 libusb 1.0.27 预编译包
2. 使用 CMake 配置：
   ```
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -DINSTALL_UDEV_RULES=OFF \
         -DCMAKE_PREFIX_PATH=/storage/Users/currentUser/usr/local/libusb-package \
         -DCMAKE_C_FLAGS="-I/storage/Users/currentUser/usr/local/libusb-package/include -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0" \
         ..
   ```
3. make -j1
4. make install DESTDIR=$TEST_PREFIX
5. make install (本地安装)
6. ohc-run.py package 打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本语法错误 | autotools 生成的 configure 在 HarmonyOS 上有问题 | 改用 CMake 构建 |
| 2 | libusb.h 找不到 | 头文件路径是 libusb-1.0/libusb.h，源码使用 #include <libusb.h> | 修改源码 include 语句为 #include <libusb-1.0/libusb.h> |
| 3 | __fd_chk undefined | FORTIFY_SOURCE 在 musl libc 中不完整 | 禁用 FORTIFY_SOURCE (-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0) |
| 4 | pthread_cancel undefined | musl libc 不支持 pthread_cancel | 移除 pthread_cancel 调用，直接用 pthread_join |

## 源码修改

- `src/librtlsdr.c`: #include <libusb.h> → #include <libusb-1.0/libusb.h>
- `src/rtl_adsb.c`: #include <libusb.h> → #include <libusb-1.0/libusb.h>
- `src/rtl_adsb.c`: 移除 pthread_cancel 调用
- `src/rtl_fm.c`: #include <libusb.h> → #include <libusb-1.0/libusb.h>
- `src/rtl_power.c`: #include <libusb.h> → #include <libusb-1.0/libusb.h>

## 依赖版本

- libusb/1.0.27 (预编译包)
- pthread (系统)
- libm (系统)

## 验证结果

```bash
$ rtl_test --help
rtl_test, a benchmark tool for RTL2832 based DVB-T receivers
Usage: [-s samplerate (default: 2048000 Hz)] ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| librtlsdr-2.0.2-ohos-aarch64.tar.gz | 940KB | 主预编译包 |
| librtlsdr-2.0.2-ohos-aarch64-debug.tar.gz | 285KB | 调试符号包 |

## 注意事项

- 需要 libusb 预编译包
- 禁用 FORTIFY_SOURCE 以避免 musl libc 兼容问题
- musl 不支持 pthread_cancel，已移除相关调用

---
**编译结束**: 2026-06-10 10:26
**最终状态**: built