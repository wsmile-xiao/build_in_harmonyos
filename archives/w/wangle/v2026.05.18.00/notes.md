# wangle v2026.05.18.00 编译记录

## 编译环境
- 编译日期: 2026-05-26
- 构建系统: CMake
- 编译器: Clang 15.0.4
- 平台: HarmonyOS (鸿蒙)

## 源码信息
- URL: file:///storage/Users/currentUser/tmp/downloads/wangle-v2026.05.18.00.tar.gz
- 版本: v2026.05.18.00
- 位置: ~/builds/wangle-v2026.05.18.00.work/
- SHA256: 9c6ce936a0306b022c328bef743d0c305e2ebacf825a1e023128bafed5c835a3

## 依赖情况
- folly v2026.05.18.00 ✅
- fizz v2026.05.18.00 ✅
- openssl 3.5.6 ✅
- boost 1.74.0 ✅ (context, filesystem, program_options, regex, thread)
- glog latest ✅
- double-conversion 3.3.0 ✅
- libevent latest ✅
- gflags latest ✅
- zlib 1.3.1 ✅
- sodium latest ✅
- fmt latest ✅

## 编译过程

### 1. 初始化
- 从本地 tarball 加载源码
- 创建构建上下文和 manifest.yaml

### 2. CMake 配置
遇到的问题及解决方案：

#### 问题 1: CMake Policy CMP0167 警告
- **原因**: CMake 3.31+ 引入新策略，默认行为变更
- **解决**: 在 CMakeLists.txt 顶部添加 policy 设置：
  ```cmake
  if(POLICY CMP0167)
    cmake_policy(SET CMP0167 NEW)
  endif()
  ```

#### 问题 2: Boost 目标重复定义
- **原因**: folly 依赖的 Boost 组件与 wangle 直接依赖的 Boost 组件冲突
- **解决**: 在 find_package(folly) 之前先查找 Boost：
  ```cmake
  find_package(Boost CONFIG QUIET)
  if(NOT Boost_FOUND)
    find_package(Boost REQUIRED COMPONENTS context filesystem program_options regex thread)
  endif()
  ```

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
- 编译成功，生成 libwangle.a 和 libwangle_test_support.a
- 有少量 OpenSSL 3.0 API 弃用警告（不影响功能）

### 4. 安装
```bash
make install DESTDIR=$TEST_PREFIX  # staging
make install                         # 本地
```

## 编译产物
- **库文件**: libwangle.a, libwangle_test_support.a
- **头文件**: /usr/local/include/wangle/ (包含完整 API)
- **CMake 配置**: /usr/local/lib/cmake/wangle/wangle-config.cmake

## 源码修改

补丁文件: `0001-CMakeLists.txt.patch`

修改内容：
1. 添加 CMake Policy CMP0167 设置，避免 CMake 3.31+ 警告
2. 在 folly 查找之前先查找 Boost，避免目标重复定义

## 知识沉淀

### L2 模式经验
1. **Boost 依赖顺序问题**: folly/wangle/mvfst 等 Facebook 库通过 FetchContent 或 find_package 引入 Boost 时，可能出现目标重复定义。解决方案：在使用 folly 的项目中提前查找 Boost。

2. **CMake Policy 管理**: 大型 CMake 项目应主动设置 CMAKE_POLICY_DEFAULT_CMPXXXX 或在项目顶部用 cmake_policy() 显式声明，避免新版本 CMake 的行为变更导致意外错误。

## 编译状态
✅ 编译成功
✅ 安装成功
⏳ 待 G0 干净构建验证
---

**编译结束**: 2026-05-26 12:26
**最终状态**: built
---

**编译结束**: 2026-05-26 12:32
**最终状态**: built
