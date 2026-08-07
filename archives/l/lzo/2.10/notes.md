# lzo 2.10 适配笔记

## 编译环境
- 构建系统: cmake (autotools config.status 在 HarmonyOS 上失败，改用 CMake)
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤
lzo 源码自带 CMakeLists.txt，使用 CMake 构建系统。

```bash
mkdir build && cd build
cmake .. -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
make -j1
make install
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | GNU config 缺少 __OHOS__ 检测 | 补丁更新 config.guess/config.sub |
| 2 | autotools config.status 失败 | HMDFS 不支持 config.status 创建临时目录 | 改用 CMake 构建系统 |
| 3 | CMake 不识别 HarmonyOS 平台 | E092: CMake 无 HarmonyOS platform module | 设置 CMAKE_SYSTEM_NAME=Linux |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|---------------|
| CMakeLists.txt | 更新 cmake_minimum_required 版本 | ✅ |
| autoconf/config.guess | 添加 HarmonyOS 检测 | ✅ |
| autoconf/config.sub | 添加 ohos 支持 | ✅ |

## Conan 配方
- 构建系统: CMake (conan.tools.cmake)
- 库名: lzo2 (liblzo2.a)
- 头文件: include/lzo/
- 测试: test_package/test.c 执行 LZO 压缩/解压往返测试
---

**编译结束**: 2026-08-07 02:54
**最终状态**: built
