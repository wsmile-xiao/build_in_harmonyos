# libfido2 1.15.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 1. 设置PKG_CONFIG_PATH识别依赖
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig

# 2. 创建build目录并配置
mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release

# 3. 编译
make -j2

# 4. 安装到staging目录
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libfido2-1.15.0

# 5. 安装到本地
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HID backend未定义 | CMakeLists.txt未识别HarmonyOS系统 | 修改CMakeLists.txt添加OHOS系统识别，设置HID backend为Linux HID |
| 2 | ppoll系统调用不可用 | HarmonyOS musl libc不支持ppoll | 修改src/hid_unix.c，用poll替代ppoll |
| 3 | libudev.h缺失 | HarmonyOS缺少libudev库 | 创建stub头文件和实现，提供必要的udev函数 |
| 4 | NULL未定义 | 源码缺少stddef.h包含 | 在相关源文件中添加#include <stddef.h> |

## 源码修改

应用了4个补丁文件：

1. **0001-CMakeLists.txt.patch**
   - 添加HarmonyOS系统识别
   - 设置HID backend为Linux HID

2. **0002-src-CMakeLists.txt.patch**
   - 添加libudev stub源文件编译
   - 修复NULL未定义问题

3. **0003-src-hid_unix.c.patch**
   - 用poll替代ppoll系统调用
   - 适配HarmonyOS musl libc

4. **0004-src-stub-udev-libudev.h.patch**
   - 创建libudev stub头文件和实现
   - 提供必要的udev函数定义

## 依赖版本

| 软件 | 版本 |
|------|------|
| libcbor | 0.11.0 |
| openssl | 1.1.1w |
| zlib | 1.3.1 |

## 验证结果

```bash
# 验证fido2-token
/storage/Users/currentUser/usr/local/bin/fido2-token --version
# 输出: fido2-token 1.15.0

# 验证fido2-assert
/storage/Users/currentUser/usr/local/bin/fido2-assert --version
# 输出: fido2-assert 1.15.0

# 验证库文件
ls -lh /storage/Users/currentUser/usr/local/lib/libfido2.so*
# lrwxrwxrwx 1 currentUser currentUser   16 May 19 22:30 libfido2.so -> libfido2.so.1.15.0
# lrwxrwxrwx 1 currentUser currentUser   16 May 19 22:30 libfido2.so.1 -> libfido2.so.1.15.0
# -rwxr-xr-x 1 currentUser currentUser 7.0M May 19 22:30 libfido2.so.1.15.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libfido2-1.15.0-ohos-aarch64.tar.gz | 7.02MB | 预编译包，包含二进制文件和库文件 |

## 注意事项

- HarmonyOS缺少libudev，需要创建stub实现
- ppoll系统调用在HarmonyOS上不可用，需要用poll替代
- HID backend需要在CMake中显式指定为Linux HID
---
**编译结束**: 2026-05-19 22:32
**最终状态**: published
---

**编译结束**: 2026-05-20 12:00
**最终状态**: built
