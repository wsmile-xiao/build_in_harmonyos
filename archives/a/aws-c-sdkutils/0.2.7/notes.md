# aws-c-sdkutils 0.2.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

使用 CMake 构建系统，通过 Conan 配方管理依赖和交叉编译工具链。关键步骤：
1. `conan create` 配方构建 aws-c-sdkutils 0.2.7，依赖 aws-c-common/0.14.3
2. CMake 配置阶段通过 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 注入 aws-c-common 的 CMake 配置路径
3. 设置 `BUILD_TESTING=OFF`、`BUILD_SHARED_LIBS=ON`
4. 编译生成 libaws-c-sdkutils.so 共享库

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMakeDeps 生成器与 AWS 自带 CMake config 命名冲突 | AWS C 库使用 `AWS::` 命名空间，CMakeDeps 会生成 `aws-c-common::aws-c-common` 目标 | 通过 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 注入辅助 cmake 文件，将依赖路径加入 `CMAKE_PREFIX_PATH`，使 `find_package(aws-c-common)` 找到包自带的 config |

## 源码修改

无补丁，aws-c-sdkutils 0.2.7 源码无需修改即可在 HarmonyOS 上编译。

## 依赖版本

- aws-c-common/0.14.3 (动态库 libaws-c-common.so)

## 验证结果

```bash
conan create . --profile=ohos-aarch64  # PASS
test_package: 1/1 PASS
conan-verify: ALL PASS (G0-G4 + L2/L4/L5)
```

---

**编译结束**: 2026-07-27
**最终状态**: built

## 最终状态

COMPLETED — aws-c-sdkutils 0.2.7 适配完成，状态: built
