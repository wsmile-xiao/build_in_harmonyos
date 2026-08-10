# odbc-cpp-wrapper 1.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-07
- 编译器: clang/clang++ 15.0.4
- 状态: published (conan-verify passed)

## 编译步骤

1. 下载源码：从 GitHub 下载 SAP/odbc-cpp-wrapper v1.6 tarball
2. 安装依赖：libiodbc 3.52.16 via cmd-pkgs
3. CMake 配置：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release \
         -DBUILD_SHARED_LIBS=OFF \
         -DODBC_INCLUDE_DIR=/storage/Users/currentUser/usr/local/include \
         -DODBC_LIBRARY=/storage/Users/currentUser/usr/local/lib/libiodbc.so \
         ..
   ```
4. 编译：`make -j2`
5. 安装到 staging：`make install DESTDIR=$TEST_PREFIX`

## Conan 适配

### conanfile.py
- 静态库构建 (BUILD_SHARED_LIBS=OFF)
- ODBC (libiodbc) 通过系统安装，在 generate() 中设置 ODBC_INCLUDE_DIR 和 ODBC_LIBRARY
- package_info() 声明 system_libs: iodbc, iodbcinst
- cmake_file_name: odbccpp, cmake_target_name: odbccpp::odbccpp

### test_package
- test.cpp: 创建 ODBC Environment (调用 SQLAllocHandle via libiodbc)
- conanfile.py: 使用 cmake.test() + self.run() 直接运行测试二进制

### conan-verify
- G0-G4 全部通过
- W3 本地 CI 模拟通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub API URL 下载后 BadZipFile | URL 无 .tar.gz 扩展名，conan 无法识别格式 | 改用 GitHub archive URL (带 .tar.gz 扩展) |
| 2 | FindODBC 无法找到 ODBC 库 | OHOS 上 find_program 找不到 iodbc-config | 在 generate() 中显式设置 ODBC_INCLUDE_DIR 和 ODBC_LIBRARY |
| 3 | CMake target name 不匹配 | cmake_target_name 未设置 namespace | 设置 cmake_target_name = "odbccpp::odbccpp" |
| 4 | test.cpp 编译错误 | EnvironmentRef 不支持 operator! | 改用 isNull() 方法 |
| 5 | W3 CI 检查 stub_test_method | test_package conanfile.py 缺少 self.run() | 添加 self.run() 直接运行测试二进制 |

## 源码修改
无源码修改，不需要补丁。

## 依赖版本
- libiodbc 3.52.16 (cmd-pkgs)
- clang 15.0.4

## 验证结果
- conan-verify: G0-G4 全部 PASS
- W3 本地 CI 模拟: PASS
- 产物: libodbccpp.a (506KB 静态库) + 20 头文件

---
**编译结束**: 2026-08-07 06:30
**最终状态**: published
