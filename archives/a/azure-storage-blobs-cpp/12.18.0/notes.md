# azure-storage-blobs-cpp 12.18.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-25
- 编译器: clang 15.0.4 (OHOS toolchain)
- 状态: built

## 编译步骤
```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 平台三分支 else() FATAL: Unsupported platform | AzureTransportAdapters.cmake 用 if(WIN32)/elseif(UNIX)/else() 判断，HarmonyOS 不匹配 UNIX 落入 else | patch 0001: elseif(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS") |
| 2 | CMakeDeps 包名未匹配 azure-storage-common | CMakeLists.txt 用 find_package(azure-storage-common-cpp) 但 CMakeDeps 生成的包名为 azure-storage-common | patch 0002: 改为 find_package(azure-storage-common) |
| 3 | test_package 运行时 libazure-core.so 未找到 | self.run() 默认 env="conanbuild" 不含运行时库路径 | 用 env="conanrun" 激活 LD_LIBRARY_PATH |
| 4 | L0d stub test_method 检测失败 | test() 方法必须含 self.run() 调用 | 改为 self.run(..., env="conanrun") |
| 5 | L0i registry 不可达 | ohpcd 远程 CDN 策略错误 (system acceleration policy not enabled) | 基础设施问题，本地缓存已满足依赖 |

## 依赖版本
- azure-core-cpp/1.16.4
- azure-storage-common-cpp/12.14.0
- azure-identity-cpp/1.13.3 (transitive)
- openssl/3.5.6
- libcurl/8.5.0
- zlib/1.3.1

## 验证结果
```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# 主包构建成功，test_package 输出: test azure-storage-blobs-cpp 12.18.0: OK
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码声明 + 2 patches |
| patches/0001-cmake-modules-AzureTransportAdapters.cmake.patch | OHOS 平台检测修复 |
| patches/0002-sdk-storage-azure-storage-blobs-CMakeLists.txt.patch | CMakeDeps 包名匹配修复 |
| test_package/ | L1 消费者测试 |

## 注意事项
- 远程 registry ohpcd 返回 CDN 策略错误，依赖发布状态需网络恢复后确认
- 本库已成功构建并验证，配方可复用
