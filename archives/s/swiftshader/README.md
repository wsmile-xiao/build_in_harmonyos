# swiftshader 软件归档

## 软件
SwiftShader — CPU 纯软件实现的 Vulkan 1.3 图形 API（软件 Vulkan ICD）

## 描述
SwiftShader 是 Google 的高性能 CPU 版 Vulkan 1.3 实现，作为可安装客户端驱动（ICD）
使用：它内置一个基于 LLVM-10 的 Reactor JIT 编译器（另有 Subzero 后端）和一套
SPIR-V 编译器，可在没有 GPU 的平台上完成 Vulkan 渲染与计算。上游 canonical 仓库在
swiftshader.googlesource.com/SwiftShader，GitHub 镜像为 github.com/google/swiftshader。

## 编译版本
- 0_git20260921（git 快照 commit `1e80438d2b93ef36a7c05f8d2b81233bac0e3d16`，2026-09-16）

## 构建系统
- CMake（>= 3.22.1），C/C++17

## 关键依赖
- 上游无 release，源码为 git 快照 tarball（含大部分 vendored 第三方）
- 默认构建额外需要两个 submodule：`third_party/googletest`、`third_party/glslang`
- Reactor 默认后端为 vendored `third_party/llvm-10.0`

## 平台适配（HarmonyOS PC / OHOS aarch64）
- 新增 HarmonyOS/OHOS 平台分支（等价 Linux，headless）：接受 `CMAKE_SYSTEM_NAME` 为
  HarmonyOS/OHOS，默认禁用 XCB/Wayland WSI
- conan 侧设 `CMAKE_SYSTEM_NAME=OHOS`、`CMAKE_SYSTEM_PROCESSOR=aarch64`
- 子模块目录由配方预先填充，避免构建期 `git submodule update`

## 归档日期
2026-09-29
