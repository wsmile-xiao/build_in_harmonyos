# clpeak 1.1.5 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt + cmake/common.cmake)
- 编译日期: 2026-09-08
- 编译器: clang/clang++ (OHOS 工具链)
- 状态: built

## 编译步骤

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DOpenCL_INCLUDE_DIR=<合并 include 目录> \
  -DOpenCL_LIBRARY=<opencl-icd-loader>/lib/libOpenCL.so
cmake --build build -j1
```

关键点：
- clpeak 的 CMakeLists 用 `find_package(OpenCL)` + `FIND_PATH(HPP_FOUND CL/opencl.hpp ...)`，
  走 CMake 标准 FindOpenCL 模块，通过 `OpenCL_INCLUDE_DIR` / `OpenCL_LIBRARY` 两个
  缓存变量喂入（clblast 配方同款模式）。
- `OpenCL_INCLUDE_DIR` 是合并目录：opencl-headers 包的 include/CL/*.h + vendor 的
  OpenCL-CLHPP include/CL/opencl.hpp（配方 generate() 中合并）。
- 本地验证：cmake 配置发现 OpenCL 3.0，15 个 TU 全部编译，生成 bin/clpeak。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `FIND_PATH(HPP_FOUND CL/opencl.hpp ...)` 失败 → 走 BuildSdk.cmake 联网 git clone OpenCL-SDK | ohpcd 的 opencl-headers 包只打包 .h，不含 C++ 绑定头 opencl.hpp | 配方内 vendor OpenCL-CLHPP v2025.07.22 的 include/CL/opencl.hpp 到合并 include 目录（clinfo 配方同款 vendoring 模式） |
| 2 | lang-preflight 判 mixed → env_unsupported | lang_detect 全文件扫描命中 android/ 子目录的 build.gradle（辅助 APK 打包示例），优先级高于顶层 CMakeLists.txt | 按 R47 边界规则复核：顶层 manifest=CMakeLists.txt（cmake）、cpp 主体 77%、android 为辅助打包不算主体 → 判 cpp 继续适配（emio-0.9.0 先例同构） |
| 3 | OHOS 无系统 libOpenCL | OHOS 系统不提供 OpenCL ICD loader | requirements 引 opencl-icd-loader/v2024.05.08（提供 libOpenCL.so），运行期由该包提供 |

## 源码修改

无补丁（patches/ 为空，源码零修改）。

## 依赖版本

| 包 | 版本 | 来源 |
|----|------|------|
| opencl-headers | 2026.05.29 | ohpcd |
| opencl-icd-loader | v2024.05.08 | ohpcd |
| OpenCL-CLHPP（vendor 头） | v2025.07.22 | KhronosGroup 上游 tarball |

## 验证结果

```bash
# test_package 运行打包二进制（2 断言）
clpeak --version  # => "clpeak version: 1.1.5", rc=0
clpeak            # 无 OpenCL ICD: "no platforms found", rc=0（上游容忍 -1001）
# 上游 CTest: clpeak_test_run 1/1 Passed（无设备时 clpeak 以 0 退出）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/clpeak | OpenCL 峰值基准测试可执行文件（ELF, armv8） |

## 注意事项

- package_type=application：只安装 bin/clpeak + LICENSE，无消费者库接口。
- 无 OpenCL ICD/平台驱动时 clpeak 打印 "no platforms found" 并以 0 退出，
  CTest 与 test_package 均可在预检机通过。
- commands.json 按 R38 放在软件级目录（archives/c/clpeak/commands.json）。
---
---

**编译结束**: 2026-09-08 00:51
**最终状态**: built
