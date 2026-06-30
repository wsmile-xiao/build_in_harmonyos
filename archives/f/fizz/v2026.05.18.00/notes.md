# fizz v2026.05.18.00 编译记录

## 编译环境
- 编译日期: 2026-05-26
- 构建系统: CMake
- 编译器: Clang 15.0.4
- 平台: HarmonyOS (鸿蒙)

## 源码信息
- URL: https://github.com/facebookincubator/fizz/archive/refs/tags/v2026.05.18.00.tar.gz
- 版本: v2026.05.18.00
- 位置: ~/tmp/builds/fizz-2026.05.18.00/fizz/

## 依赖情况
- fmt 11.0.2 ✅
- double-conversion 3.3.0 ✅
- boost 1.74.0 ✅ (context, filesystem, program_options, regex)
- folly v2026.05.18.00 ✅
- openssl 3.5.6 ✅
- libsodium 1.0.18 ✅
- glog ✅
- zstd ✅
- libevent ✅

## 编译过程

### 1. 初始化
- 源码已存在于本地目录
- 手动创建构建上下文和 manifest.yaml

### 2. CMake 配置
遇到的问题及解决方案：

#### 问题 1: Boost 组件找不到
- **原因**: BoostConfig.cmake 配置为 header-only，创建了 stub libraries
- **解决**: 修改 BoostConfig.cmake，添加真实的静态库路径（Boost 1.74.0）

#### 问题 2: FindSodium.cmake 不支持平台
- **原因**: FindSodium.cmake 只支持 UNIX 和 WIN32，HarmonyOS 未被识别为 UNIX
- **解决**: 修改 FindSodium.cmake，添加 fallback 支持未知 Unix-like 平台

#### 问题 3: GTest 缺失
- **原因**: BUILD_TESTS=ON 默认启用，需要 GTest
- **解决**: 设置 -DBUILD_TESTS=OFF

#### 问题 4: Folly::folly_benchmark 缺失
- **原因**: BUILD_EXAMPLES=ON 默认启用，需要 benchmark 目标
- **解决**: 设置 -DBUILD_EXAMPLES=OFF

最终 CMake 配置命令：
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_PREFIX_PATH=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTS=OFF \
  -DBUILD_EXAMPLES=OFF
```

### 3. 编译
```bash
make -j2
```
- 编译成功，生成 libfizz.a 和 libfizz_test_support.a
- 有 OpenSSL 3.0 EC_KEY API 弃用警告（不影响功能）

### 4. 安装
```bash
make install DESTDIR=$TEST_PREFIX  # staging
make install                         # 本地
```

## 编译产物
- **库文件**: libfizz.a (6.0M), libfizz_test_support.a (333K)
- **头文件**: /usr/local/include/fizz/ (包含完整 API)
- **CMake 配置**: /usr/local/lib/cmake/fizz/fizz-config.cmake

## 知识沉淀
1. **L1 平台真理**:
   - HarmonyOS CMake 配置时 UNIX=1，但部分 Find*.cmake 模块不识别
   - 需要修改 FindSodium.cmake 支持 fallback

2. **L2 模式经验**:
   - Boost header-only + compiled components 混合安装时需自定义 BoostConfig.cmake
   - fizz/wangle/mvfst 等 Facebook 库通常需要禁用 BUILD_TESTS 和 BUILD_EXAMPLES

## 编译状态
✅ 编译成功
✅ 安装成功
⏳ 待打包和收尾
---

**编译结束**: 2026-05-26 11:11
**最终状态**: built
