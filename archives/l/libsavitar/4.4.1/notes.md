# libsavitar 4.4.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 上游核验：git ls-remote 确认正式标签 v4.4.1（commit 6bdeebcaefbf05ead3a2072e5b9759b9aee8cc2c，peeled 4e0baf3207943b0459268dd60c88888dea44f0a3），tarball sha256=b65dba135fceb40d991ed02d05b73e417e1a4843760bc262334379ecdb3fe4a1。
2. init-build libsavitar 4.4.1 --url=<官方 tarball>（注意：直接给 git 仓库 URL 会被下载为 HTML，必须给 archive/refs/tags/v4.4.1.tar.gz）。
3. lang-preflight：任务语言 cpp，检测 cpp，匹配通过。
4. 手动编译验证（库本体）：
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
     -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
     -DBUILD_PYTHON=OFF -DBUILD_TESTS=OFF
   cmake --build . -j4   # libSavitar.so 构建成功
   ```
   - CMake 4.x 需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（cmake_minimum_required(3.6) 兼容）。
   - 库本体 C++11 可编译，不需要提高标准。
5. 上游测试（R51 实测）：
   - GTest 通过 ohpcd 制品仓安装（gtest/1.17.0），显式传入 GTEST_INCLUDE_DIR/LIBRARY/MAIN_LIBRARY。
   - 测试编译需 C++17（gtest 1.17 使用 std::make_index_sequence），将 CMakeLists.txt 内 `set(CMAKE_CXX_STANDARD 11)` 改为 17（仅测试构建需要；库本体仍 11 兼容）。
   - ctest 3/3 过（ThreeMFParserTest 3 用例 + MeshDataTest 2 用例，共 5 断言全过）。
   - 运行测试二进制需 LD_LIBRARY_PATH 包含 build 目录（环境 LD_LIBRARY_PATH 指向旧安装前缀导致 relocation 失败）。
6. conan-init 后重写配方为 CMake 版：关闭 BUILD_PYTHON（SIP 绑定）、BUILD_TESTS，映射 BUILD_STATIC=shared 选项，pugixml 内嵌无需 requires。
7. test_package：改为 C++ 消费者测试，真实调用 Savitar::ThreeMFParser::parse / sceneToString 解析最小 3MF 模型（非空壳，R34）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build --url=<git 仓库 URL> 下载到 HTML | 下载器直接把 git 仓库页当文件抓取 | 改用 archive/refs/tags/v4.4.1.tar.gz tarball |
| 2 | CMake 4.1.2 配置报 policy 错误 | cmake_minimum_required(3.6) 与 CMake 4.x 兼容策略 | 加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5（配方 generate() 写入） |
| 3 | 测试编译 gtest/gtest.h not found | 上游用模块化 find_package(GTest)，conan CMakeDeps 目标名不匹配 | 显式传 GTEST_INCLUDE_DIR/GTEST_LIBRARY/GTEST_MAIN_LIBRARY |
| 4 | gtest 1.17 头文件报 make_index_sequence 不存在 | gtest 1.17 需 C++14+，项目固定 C++11 | 测试构建提高 CMAKE_CXX_STANDARD=17 |
| 5 | 测试二进制运行 relocation symbol not found | 环境 LD_LIBRARY_PATH 指向无该符号的旧库 | 运行前 LD_LIBRARY_PATH 前置 build 目录 |

## 源码修改

无 upstream 源码修改；仅 CMakeLists.txt 测试构建标准 11→17（开发验证用途，配方通过 BUILD_TESTS=OFF 不涉及）。

## 依赖版本

- gtest/1.17.0（ohpcd 制品仓，仅测试构建）

## 验证结果

```bash
# 库本体构建
cmake --build . -j4  → 100% 成功，libSavitar.so

# 上游测试（ctest）
Tests Passed: 3/3（ThreeMFParserTest 3/3，MeshDataTest 2/2，共 5 断言）
```
---

**编译结束**: 2026-09-27 18:20
**最终状态**: built
