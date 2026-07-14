# cpputest 4.0_r2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-13
- 编译器: clang/clang++
- 状态: published

## 版本号说明
- 上游 GitHub tag: v4.0
- Issue 描述版本: 4.0-r2 (打包修订版)
- Conan 版本号: 4.0_r2 (Conan 版本号不允许包含 "-")

## 编译步骤

1. **源码获取**: 从 GitHub 下载 cpputest v4.0 源码包 (tar.gz)
2. **Conan 配方**: 编写 `conanfile.py` (CMake 库模式, 参考 charls/2.4.3)
3. **CMake 配置**:
   - 设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` (OHOS 适配)
   - 设置 `BUILD_SHARED_LIBS=OFF` (默认静态库)
   - 禁用 `TESTS` + `EXAMPLES` (加速构建)
   - 启用 `EXTENSIONS` + `MEMORY_LEAK_DETECTION` (核心功能)
   - 启用 `C++11` (现代 C++ 支持)
4. **CMake 构建**: `cmake.configure()` + `cmake.build()`
5. **打包**: `cmake.install()` 安装库文件 + 头文件 + CMake 配置
6. **测试**: test_package 用 cpputest 编写 6 个单元测试, 验证框架可用

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 OHOS 平台 | E092: CMake 未内置 OHOS 平台定义 | 设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` |
| 2 | profile 中编译器路径在本地不存在 | CI 环境 profile 引用了 HNP 特定路径 | 使用 `shutil.which()` 查找 clang/clang++ 并替换 toolchain 文件中的路径 |
| 3 | 版本号 4.0-r2 中的 "-" 不合法 | Conan 版本号不允许包含 "-" | 使用 `4.0_r2` 作为 Conan 版本号, 目录名与之一致 |
| 4 | 上游测试需要 CTest 框架 | 上游测试由 TESTS=ON 构建 | 关闭 TESTS, test_package 使用自带测试 |

## 依赖版本

- cpputest: 4.0 (上游 v4.0 tag, 无第三方依赖)

## 验证结果

```bash
# test_package smoke test
./test_cpputest
# 预期输出:
# .
# OK (6 tests, 6 ran, 6 checks, 0 ignored, 0 filtered out, 0 ms)
```

## 注意事项

- cpputest 是 C/C++ 单元测试框架, 无第三方依赖, 构建简单
- 默认构建为静态库, 生成 CppUTest + CppUTestExt 两个库
- 支持内存泄漏检测和测试桩扩展
- 上游测试未在鸿蒙平台运行, test_package 使用自带测试验证基本功能
- 版本号 4.0-r2 中的 "-" 在 Conan 中用 "_" 替代为 4.0_r2
