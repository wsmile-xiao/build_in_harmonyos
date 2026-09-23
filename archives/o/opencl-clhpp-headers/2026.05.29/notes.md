# Notes — opencl-clhpp-headers 2026.05.29

## 适配概要

- **软件**: OpenCL C++ API headers (Khronos Group)
- **版本**: 2026.05.29
- **构建系统**: CMake (header-only INTERFACE library)
- **类型**: header-only library（无 .so/.a 产物）
- **依赖**: opencl-headers/2026.05.29（C API 头文件）

## 编译过程

1. 源码来自 GitHub tag v2026.05.29
2. CMake 构建系统识别为 INTERFACE library（`add_library(HeadersCpp INTERFACE)`）
3. 无需实际编译，只需安装 `include/CL/*.hpp` 到 `include/CL/`
4. 上游测试需要 CMock submodule + ruby，鸿蒙环境支持

## 上游测试本地运行 (R51)

### 环境准备
- Ruby 3.4.5 (/data/service/hnp/bin/ruby) ✅
- Git 2.45.2 (/data/service/hnp/bin/git) ✅
- CMock + Unity submodule 手动初始化 ✅
- Clang 15.0.4 + CMake 4.1.2 ✅

### 测试结果
- test_openclhpp.cpp: 12 个变体（6 版本 × 2 选项组），每变体 173 个测试
  - 通过: 172/173 = 99.4%
  - 失败: testContextFromType (CMock mock 期望值不匹配，非头文件 bug)
- test_versions.cpp: 需 OpenCL ICD Loader，无法运行
- pkgconfig: 需 OpenCL ICD Loader，无法运行

## Conan 配方要点

- `package_type = "header-library"`
- `requires("opencl-headers/2026.05.29")` — 依赖 C API 头文件
- `package()` 复制 `include/CL/*.hpp` 到 `include/CL/`
- `package_id()` 清空（header-only 无构建依赖）
- test_package: 4 个测试文件，18 个编译期断言

## 构建配置

- `-DBUILD_DOCS=OFF` — 跳过文档生成
- `-DBUILD_EXAMPLES=OFF` — 跳过示例编译
- `-DBUILD_TESTING=OFF` — CI 跳过测试（需 CMock + ruby，CI 无法自动初始化）

---

**编译结束**: 2026-09-05 16:35
**最终状态**: published
**上游测试通过率**: 172/173 (99.4%)
