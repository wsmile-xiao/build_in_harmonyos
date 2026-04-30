# 编译进度记录 — hidapi 0.14.0

## 编译开始

**时间**: 2026-04-30 11:00

**目标**: 编译 hidapi 0.14.0（HID 设备访问库）

---

## 步骤记录

### Step 1: 源码获取

- **URL**: https://github.com/libusb/hidapi/archive/refs/tags/hidapi-0.14.0.tar.gz
- **方法**: 手动下载（自动搜索失败）
- **结果**: ✅ 成功下载到本地（340K）

---

### Step 2: 构建系统选择

- **原始系统**: autotools + CMake 双支持
- **遇到问题**: autotools bootstrap 失败（libtoolize 函数缺失、config.guess/config.sub 缺失）
- **解决方案**: 使用 CMake 构建
- **结果**: ✅ 切换到 CMake

---

### Step 3: CMake 配置

**尝试 1**: 
- 问题: CMake 版本兼容性（要求 3.1.3，系统 4.1.2 要求最低 3.5）
- 解决: 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`

**尝试 2**:
- 问题: Iconv 未找到
- 解决: 添加 `-DHIDAPI_NO_ICONV=ON` 禁用 Iconv

**最终配置参数**:
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         -DHIDAPI_NO_ICONV=ON
```

**结果**: ✅ 配置成功
- 检测到 libusb-1.0 (version 1.0.29) ✅
- 检测到 Threads::Threads ✅

---

### Step 4: 编译

```bash
cmake --build .
```

**结果**: ✅ 编译成功
- 构建目标: hidapi_libusb (共享库)
- 产物: libhidapi-libusb.so

---

### Step 5: 安装（Staging）

```bash
cmake --build . --target install DESTDIR=/storage/Users/currentUser/tmp/test-install-hidapi-0.14.0
```

**结果**: ✅ 安装成功
- 库文件: libhidapi-libusb.so
- 头文件: hidapi.h, hidapi_libusb.h
- pkg-config: hidapi-libusb.pc
- cmake 配置: hidapi-config.cmake 等

---

### Step 6: 本地安装

```bash
cmake --build . --target install
```

**结果**: ✅ 安装成功到 ~/usr/local

**验证**:
```bash
pkg-config --modversion hidapi-libusb
# 输出: 0.14.0 ✅
```

---

## 编译结束

**最终状态**: success

**关键问题**:
1. autotools 构建失败 → 切换 CMake
2. CMake 版本兼容性 → 添加 POLICY_VERSION_MINIMUM
3. Iconv 缺失 → 禁用 Iconv (HIDAPI_NO_ICONV)

**构建产物**:
- 共享库: libhidapi-libusb.so
- 头文件: hidapi/hidapi.h, hidapi/hidapi_libusb.h
- pkg-config: hidapi-libusb.pc

**依赖**: libusb-1.0 (已安装)

---

**时间**: 2026-04-30 11:15