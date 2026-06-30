# libzen 0.4.41 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-20
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. **源码下载与解压**
   - URL: https://mediaarea.net/download/source/libzen/0.4.41/libzen_0.4.41.tar.gz
   - 嵌套源码提升: Project/CMake → libzen-0.4.41.work
   - 源码复制: 将 ZenLib/Source 复制到工作目录顶层

2. **Configure**
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_BUILD_TYPE=Release ..
   ```
   - 耗时: 8s
   - 检测到线程库、大文件支持

3. **Make**
   ```bash
   make -j1
   ```
   - 耗时: 15s
   - 输出: libzen.so (383KB)
   - 警告: 3个隐式转换警告（非关键）

4. **Install (DESTDIR模式)**
   ```bash
   make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libzen-0.4.41
   ```
   - 产物: libzen.so + 头文件 + pkg-config + cmake config

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本要求过低 | cmake_minimum_required(VERSION 3.1.0) 与 CMake 4.1.2 不兼容 | 更新为 3.5.0 |
| 2 | 源码路径不正确 | 嵌套源码提升后路径 ../../Source 不存在 | 改为 Source |
| 3 | pthread_cancel 未定义 | HarmonyOS 不支持 pthread_cancel | 添加 `#if !defined(__OHOS__)` 守卫 |
| 4 | G4 质量门禁失败 | manifest.yaml system 字段为 autotools | 改为 cmake |

## 源码修改

### 1. CMakeLists.txt
- 第1行: `cmake_minimum_required(VERSION 3.1.0)` → `3.5.0`
- 第24-26行: `../../Source` → `Source`

### 2. Source/ZenLib/Thread.cpp
- 第521-523行: 添加 `&& !defined(__OHOS__)` 条件
  ```cpp
  #if !defined(__ANDROID_API__) && !defined(__OHOS__)
      pthread_cancel((pthread_t)ThreadPointer);
  #endif
  ```

## 依赖版本

- 无外部依赖（仅依赖 pthread）

## 验证结果

### 编译验证
```bash
pkg-config --modversion libzen
# 0.4.41

pkg-config --cflags libzen
# -DUNICODE -I/storage/Users/currentUser/usr/local/include

pkg-config --libs libzen
# -L/storage/Users/currentUser/usr/local/lib -lzen -lpthread
```

### 功能验证
测试程序 test_libzen.cpp 通过 5 项核心功能测试：
- ✅ Ztring UTF8 编解码
- ✅ Ztring size
- ✅ File.Exists
- ✅ Ztring.empty
- ✅ Ztring 赋值操作

详细测试报告见: reports/test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libzen-0.4.41-ohos-aarch64.tar.gz | 644KB | 预编译包（已签名） |
| libzen-0.4.41-ohos-aarch64-debug.tar.gz | 182KB | Debug符号包 |
| 0001-Source-ZenLib-Thread.cpp.patch | 16KB | 平台适配补丁 |

## 注意事项

1. libzen 是纯库，无可执行文件
2. 使用时需设置 `PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig`
3. 依赖此库的项目需链接 pthread: `-lpthread`
4. Thread::ForceTerminate() 在 HarmonyOS 上为空操作（不调用 pthread_cancel）

---
**编译结束**: 2026-05-20 11:21
**最终状态**: published
**测试结果**: PASS (10/10 tests)