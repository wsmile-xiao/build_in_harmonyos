# libopencad 0.2.0 适配笔记

## 基本信息

- 库名：libopencad（conan 包名）
- 版本：0.2.0
- 上游仓库：https://github.com/nextgis-borsch/lib_opencad
  - 原仓库 sandyre/libopencad 已弃用（README 指向 nextgis-borsch/lib_opencad）
  - 上游最新 tag 为 v0.3.5，本任务认领版本为 v0.2.0
- 语言：**C++11**（认领信息写"C"，实际为 C++11，PR 中需纠正）
- 构建系统：CMake（cmake_minimum_required 2.8.12）
- 许可证：MIT

## 关键决策

1. **project 名映射（opencad → libopencad）**
   - 上游顶层 CMakeLists 为 `project(opencad)`，静态库产物名为 `opencadstatic`，
     头文件安装到 `<prefix>/include/opencad/`。
   - conan 包名保持认领名 `libopencad`，`package_info` 中 `cpp_info.libs = ["opencadstatic"]`
     指向实际产物，`includedirs = ["include"]` 暴露头文件目录。

2. **零外部依赖**
   - 阶段2 扫描确认库本体全部 include 仅为 C++ 标准库 + 自带头文件，
     `MacTypes.h` 在 `#ifdef __APPLE__` 条件块内，OHOS 不受影响。
   - 因此主配方 `requirements` 为空，无需 conancenter/ohpcd 依赖解析。

3. **BUILD_SHARED_LIBS=OFF（静态库）**
   - 静态库方案避免 OHOS 设备上运行时依赖问题，且上游静态库（opencadstatic）为默认形态。
   - 配方通过 CMakeToolchain 固定 `BUILD_SHARED_LIBS=OFF`、`BUILD_APPS=OFF`、`BUILD_TESTS=OFF`。

4. **-std=c++11 硬编码处理**
   - 上游顶层 CMakeLists 硬编码 `set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")`。
   - ohos-aarch64 profile 的 compiler.cppstd=17，两者不冲突（C++17 兼容 C++11 源码），
     clang15 实测可正常编译，无需剥离 flag。

## 遇到的问题与解决方案

conan create 共重试 11 次，编译相关失败与修复如下（日志：仓库根 logs/conan-create-N.log）：

1. **SHA256 不匹配**（第1次）：conandata.yml 初版用了 api.github.com tarball 的哈希
   （dfc6e160...），而下载 URL 是 github.com/archive/refs/tags/ 的 tarball，两者顶层
   目录名不同（api 版为 nextgis-borsch-lib_opencad-<short-sha>，archive 版为
   lib_opencad-0.2.0），gzip 字节不同 → 哈希不同。修复：改为实测的 archive URL 哈希
   b7bf09fc...。
2. **CMake <3.5 兼容已移除**（第2、3次）：上游 cmake_minimum_required(2.8.12) 与本机
   CMake 4.1.2 冲突。经 CMakeToolchain 变量注入 CMAKE_POLICY_VERSION_MINIMUM=3.5 无效
   （toolchain 变量读取时机早于 cmake_minimum_required 校验），改用
   cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"]) 生效。
3. **configure_file 输入目录错误**（第4次）：上游顶层 CMakeLists.txt 的
   configure_file(${CMAKE_MODULE_PATH}/uninstall.cmake.in ...) 在 conan toolchain 向
   CMAKE_MODULE_PATH 前置 generators 目录后，CMake 4.1 列表展开异常。修复：补丁
   patches/0001-cmake-configure-file.patch 改用 ${CMAKE_SOURCE_DIR}/cmake/uninstall.cmake.in。
4. **补丁 hunk 行号偏移**（第5次）：0001 补丁 @@ 行号起点错 1 行，修正后应用成功。
5. **package() 中 self.copy 不存在**（第6次）：ConanFile 无 copy 方法，且 cmake.install()
   已装好头文件/库，删除冗余行。
6. **cpp_info.libs 名称错误**（第7次）：上游静态库目标为 ${PROJECT_NAME}static，配方强制
   PROJECT_NAME=libopencad 后产物为 liblibopencadstatic.a，cpp_info.libs 需为
   "libopencadstatic"（conan 自动加 lib 前缀），而非 "opencadstatic"。
7. **test_package 头文件路径**（第8次）：包头文件装到 include/opencad/，消费者需
   #include "opencad/opencad_api.h"（带前缀）。
8. **test() 属性名**（第9次）：self.cpp.build.dir 不存在，改用 self.cpp.build.bindir +
   self.build_folder。
9. **GetVersion() 断言错误**（第10次）：测试代码断言 GetVersion()==0，实际 0.2.0 返回
   major*10000+minor*100+rev=200，修正断言。
10. **上游 GTest 测试编译**：gtest 1.17.0 要求 ≥C++17（toolchain 默认 17，临时工程勿降级）；
    gtest 配方仅提供 gtest::gtest 无 gtest_main，需自带 main；上游测试 include 私有头
    dwg/io.h，需把源码 lib/ 目录加入 include path。

## 测试说明

- 上游测试：GTest 框架，22 用例 / 80 断言（io_check 14 + reading_geometries 8），
  附带 tests/data/r2000/ 8 个 DWG 样例文件；`BUILD_TESTS=OFF` 默认关闭，需显式开启。
- 测试依赖 gtest/1.17.0（ohpcd 制品仓已有）。
- 消费者 test_package 将真实调用公开 API（打开 DWG 文件、读取图层/几何信息）。

## 预期风险

- FreeBSD 已知问题：cadheader.cpp:478 处 time_t→CADVariant 二义性转换，
  新编译器可能报错（该 port 已修复），clang15 首轮编译需验证。
- 旧 CMake 2.8.12 语法在 CMake 3.x 下可能产生告警（非致命）。
