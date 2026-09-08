# nvtx 3.6.0-c-cpp 适配笔记

## 编译环境
- 构建系统: cmake (cmake_minimum_required 3.19, project(nvtx3 VERSION 3.6.0))
- 编译日期: 2026-09-06
- 编译器: clang/clang++ (LLVM 15, OHOS 交叉工具链)
- 状态: built

## 编译步骤

```bash
# 官方源码 (NVIDIA/NVTX tag v3.6.0-c-cpp, sha256=e57e9715...)
# conan create 流程：
#   conanfile.py 使用 CMakeToolchain + CMake
#   generate(): NVTX3_INSTALL=ON
#   configure -> build -> cmake.install()
# 安装内容: include/ 头文件 + lib/libnvtxw3-loader.a + lib/cmake/nvtx3 包文件
```

上游 CMake 目标:
- `nvtx3-c`        INTERFACE  (C API 头文件, include/nvtx3/ + include/nvtxw3/)
- `nvtx3-cpp`      INTERFACE  (C++ API, include/nvtx3/nvtx3.hpp)
- `nvtxw3-loader`  STATIC     (src/nvtxw3_loader.c: nvtxwLoad/nvtxwUnload, dlopen/dlsym)

依赖: 无第三方包；nvtx3-c INTERFACE 仅链接 ${CMAKE_DL_LIBS}（dl）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直连 GitHub 下载超时 | 网络环境 | 用 curl 下载官方 tarball 后 `--no-download` 复用；conandata.yml 保留官方 URL（R39），CI 侧有镜像 fallback |
| 2 | init-build 将构建系统误判为 autotools | NVTX 无 autotools 信号，init 未能识别 CMake 骨架 | manifest.yaml/build_system 与 conanfile.py 按真实 CMake 构建修正 |
| 3 | 主 worktree 的 archives/l/libXext 出现 CASE 伪差异 | hmdfs 大小写不敏感，HEAD 含 libXext/libxext 两个变体目录，checkout 碰撞 | 基线噪声隔离：不 stage、不提交、不进 PR |

## 源码修改

无（无需平台宏补丁；nvtxw3_loader.c 的 dlopen/dlsym 在 OHOS 可用）。

## 依赖版本

- 无第三方运行时依赖

## 验证结果

```bash
# conan create 验证 + test_package 消费者测试 (test_nvtx.cpp)
# test_package: find_package(nvtx3) -> nvtx3::nvtx3-cpp + nvtx3::nvtxw3-loader
# 断言: scoped_range/mark + nvtxNameOsThreadA + loader 缺失后端优雅返回
---

**编译结束**: 2026-09-06 02:10
**最终状态**: built
