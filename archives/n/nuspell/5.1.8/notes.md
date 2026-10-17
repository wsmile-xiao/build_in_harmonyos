# Nuspell 5.1.8 适配笔记

## 基本信息
- 上游仓库: https://github.com/nuspell/nuspell
- 版本: v5.1.8
- 构建系统: CMake (CMakeLists.txt)
- 语言: C++17
- 许可证: LGPL-3.0-or-later

## 依赖
- icu4c/77 (已发布到制品仓，静态链接)
  - 上游 CMake `find_package(ICU 60 REQUIRED COMPONENTS uc)`
  - 通过 `CMakeDeps.set_property("icu4c", "cmake_file_name", "ICU")` 映射

## 构建配置
- BUILD_SHARED_LIBS=OFF (静态编译, R26)
- BUILD_TESTING=OFF (Catch2 FetchContent 需网络，CI 无网络)
- BUILD_TOOLS=ON (生成 nuspell CLI 工具)
- BUILD_DOCS=OFF

## 平台适配
- 无需平台补丁，CMake 原生支持交叉编译
- OHOS 平台通过 Conan profile 配置 aarch64-linux-ohos 工具链
- settings.os 检查 in ("Linux", "OHOS") (R32)

## 产物
- lib/libnuspell.a - 拼写检查库
- bin/nuspell - CLI 拼写检查工具
- include/nuspell/ - 头文件

## 测试
- test_package 验证库链接和 API 可用性
- 创建 nuspell::Dictionary 实例测试符号链接
