# libindi 2.2.2 编译笔记

## 编译信息

- **软件名称**: libindi
- **版本**: 2.2.2
- **构建系统**: CMake
- **编译日期**: 2026-06-04

## 编译过程

### Step 1: 环境初始化

从 GitHub 下载源码：https://github.com/indilib/indi/archive/refs/tags/v2.2.2.tar.gz

### Step 2: CMake 配置

libindi 使用 CMake 构建系统。由于 CMake 不识别 HarmonyOS 平台（E092），需要设置：
```bash
cmake -B build -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
```

### Step 3: 源码修改

#### 修改 1: CMakeLists.txt
- 添加 `link_libraries(c++ c++abi)` 链接 C++ 标准库
- 处理 M_LIB 查找失败的情况
- 移除 `FATAL_ON_MISSING_REQUIRED_PACKAGES`

#### 修改 2: libs/indibase/indigpsinterface.cpp
- 将 `stime()` 替换为 `clock_settime()`（stime syscall 不可用）

#### 修改 3: libs/indicore/sharedblob.c
- 添加 `__OHOS__` 宏检测
- OHOS 不支持 mremap syscall，使用 munmap+mmap 兼容路径

#### 其他 CMakeLists.txt 修改
- examples/tutorial_six/CMakeLists.txt
- indiserver/CMakeLists.txt
- libs/indibase/CMakeLists.txt
- libs/sockets/CMakeLists.txt
- tools/CMakeLists.txt

### Step 4: 编译与安装

```bash
cmake --build build
cmake --install build DESTDIR=$TEST_PREFIX
```

### Step 5: 质量门禁验证

- G1: 二进制完整性 ✅ PASS
- G2: 功能可用性 ✅ PASS（⚠️ 1个警告）
- G3: 可移植性 ✅ PASS
- G4: 档案完整性 ✅ PASS

## 编译产物

- **bin/indiserver**: INDI 服务器可执行文件（995KB）
- **lib/libindiclient.a**: INDI 客户端静态库（3.9MB）
- **include/libindi/**: INDI 头文件（约 1.7MB）

## 依赖关系

libindi 依赖以下库：
- cfitsio (CFITSIO)
- nova (libnova)
- libusb1 (libusb-1.0)
- curl (libcurl)
- gsl (GNU Scientific Library)
- jpeg (libjpeg)
- zlib

## 已知问题

1. **G0 干净构建验证失败**: clean-verify 脚本尝试运行 configure，但 libindi 使用 CMake，不是 autotools
2. **知识草稿未完成**: 需填写 E200, E097-E102 的知识草稿内容

---

**编译结束**: 2026-06-05 15:49
**最终状态**: built（编译成功，待完成知识整理）
---

**编译结束**: 2026-06-05 15:53
**最终状态**: built
