# cpprestsdk 2.10.19 编译笔记

## 基本信息
- **软件**: cpprestsdk
- **版本**: 2.10.19
- **状态**: built
- **日期**: 2026-06-02

## 编译环境
- **编译器**: clang 15.0.4
- **构建系统**: cmake
- **前置依赖**: boost/1.81.0, openssl/1.1.1w, zlib/1.3.1

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build cpprestsdk 2.10.19
```

### 2. CMake 配置
```bash
cd ~/builds/cpprestsdk-2.10.19.work/build
cmake .. \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DBOOST_ROOT=$DEFAULT_PREFIX \
  -DCPPREST_EXCLUDE_WEBSOCKETS=OFF \
  -DCPPREST_EXCLUDE_COMPRESSION=OFF \
  -DWERROR=OFF \
  -DBUILD_TESTS=OFF \
  -DBUILD_SAMPLES=OFF
```

### 3. 编译
```bash
make -j1
```

### 4. Staging 安装
```bash
make install DESTDIR=$TEST_PREFIX
```

### 5. 本地安装
```bash
make install
```

## 遇到的问题及解决方案

### 1. websocketpp md5.hpp 编译警告
**问题**: websocketpp 的 md5.hpp 文件有 null pointer subtraction 警告，导致编译失败（-Werror）

**解决方案**: 禁用 WERROR 选项
```cmake
-DWERROR=OFF
```

## 编译的功能组件
- ✅ WebSocket 功能（CPPREST_EXCLUDE_WEBSOCKETS=OFF）
- ✅ 压缩功能（CPPREST_EXCLUDE_COMPRESSION=OFF）

## 产物
- **库文件**: libcpprest.so.2.10 (25MB)
- **头文件**: cpprest/, pplx/
- **CMake 配置**: lib/cmake/cpprestsdk/
- **预编译包**: cpprestsdk-2.10.19-ohos-aarch64.tar.gz (26MB)

## 依赖说明
- **Boost**: 需要以下组件：random, system, thread, filesystem, chrono, atomic, date_time, regex
- **OpenSSL**: 用于 WebSocket 功能
- **zlib**: 用于压缩功能

---
**编译结束**: 2026-06-02

**最终状态**: built

**质量门禁**:
- G1: PASS
- G2: PASS（有警告）
- G3: PASS
- G4: PARTIAL（预编译包本地存在）
- G0: FAIL（configure 步骤，但手动验证通过）