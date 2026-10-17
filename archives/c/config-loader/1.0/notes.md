# config-loader 1.0 适配笔记

## 编译环境
- 构建系统: cmake（CMakeLists.txt, C++17, header-first + 单 cpp 静态库）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos, HarmonyOS PC 平台)
- 状态: built

## 编译步骤

```bash
# 上游原样静态构建（子模块 tinyxml2/Catch2/jsoncpp/yaml-cpp 已下载到 third-party/）
cmake -S . -B build-static -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_STANDARD=17 -DBUILD_SHARED_LIBS=OFF -DYAML_BUILD_SHARED_LIBS=OFF
cmake --build build-static -j2          # 构建成功，exit 0
./build-static/bin/config_loader_test   # 上游全量测试，exit 0

# staging 安装验证
cmake --install build-static --prefix $TEST_PREFIX
```

- 上游 CMake bug 修复（最小补丁）：`test/ut/CMakeLists.txt` 中 `copy_configs`
  自定义目标使用全局 `CMAKE_RUNTIME_OUTPUT_DIRECTORY`（CMake 4.x 下为空导致
  复制到根目录 `/configs` 失败），改为 `${CMAKE_BINARY_DIR}/bin/configs`。
- 动态库运行时符号缺失（bionic loader + libc++_shared.so ABI 不匹配）：
  探索阶段改用静态链接构建（-DBUILD_SHARED_LIBS=OFF），测试全量通过。

## 上游测试申报表（R51 三步法清点）

测试框架：Catch2（v3 风格，`SCENARIO`=TEST_CASE 别名，BDD 风格）
可执行：`config_loader_test`（单二进制，test/ut/CMakeLists.txt 注册）

| 测试源文件 | SCENARIO 数 | 条件编译 | 实例化 |
|---|---|---|---|
| ConstexprStringTest.cpp | 2 | 无 | ✅ |
| DeserializerTest.cpp | 1 | 无 | ✅ |
| JsonCppDeserializeTest.cpp | 4 | 无 | ✅ |
| JsonCppTest.cpp | 2 | #ifdef HAS_JSONCPP | ✅ |
| ReflectMacroTest.cpp | 1 | 无 | ✅ |
| ResultChecking.cpp | 1 | 无 | ✅ |
| SerializerTest.cpp | 2 | 无 | ✅ |
| TinyXML2DeserializeTest.cpp | 7 | 无 | ✅ |
| TinyXML2Test.cpp | 1 | #ifdef HAS_TINYXML2 | ✅ |
| TypeSerializerTest.cpp | 2 | 无 | ✅ |
| UtilsTest.cpp | 1 | 无 | ✅ |
| YamlCppDeserializeTest.cpp | 4 | 无 | ✅ |
| YamlCppTest.cpp | 1 | #ifdef HAS_YAMLCPP | ✅ |
| **合计** | **29** | | |

- source_declared_total: **29**（13 个用户测试源文件，可复制枚举：`grep -c "SCENARIO"`）
- configured_executable_total: **29**（当前 OHOS 配置 HAS_TINYXML2/HAS_JSONCPP/HAS_YAMLCPP 均 ON，
  无互斥排除，全部注册进 config_loader_test）
- executed_passed_total: **29**（运行 `./config_loader_test`，输出
  "All tests passed (352 assertions in 29 test cases)"，exit 0）
- 失败: 0；未运行/未实例化: 0
- 全量通过率: **29/29 = 100%**

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时，init-build 下载失败 | 网络不通 github 直连 | 用 codeload.github.com 镜像下载 v1.0 tag tarball（SHA-256 已核验），init-build 复用 |
| 2 | conan download 报 No space / sqlite 错误 | /tmp 为只读 erofs 挂载（E002） | 设 TMPDIR/TMP/TEMP=~/tmp（360GB free），重试成功 |
| 3 | make 构建失败: copy_configs 复制到 /configs | 上游 CMake bug：全局 CMAKE_RUNTIME_OUTPUT_DIRECTORY 为空 | 最小补丁改为 ${CMAKE_BINARY_DIR}/bin/configs |
| 4 | 测试运行 symbol not found（yaml/Catch2 RTTI） | bionic loader + libc++_shared.so ABI 不匹配 | 静态链接构建（BUILD_SHARED_LIBS=OFF），测试全量通过 |
| 5 | cmake --install 创建 usr/local/lib 报 ENOSPC | 存储瞬时压力/临时限制 | 恢复后重试成功（--prefix staging） |

## 源码修改

- `test/ut/CMakeLists.txt`：`copy_configs` 目标路径修复（见上，将进入 patches/）

## 依赖版本

- tinyxml2: 子模块最新（对应 upstream git），制品仓已发布 10.0.0/10.1.0/11.0.0
- jsoncpp: 子模块最新，制品仓已发布 1.9.5/1.9.8/1.9.8.1
- yaml-cpp: 子模块最新，制品仓已发布 0.8.0/0.9.0
- Catch2: 子模块最新（v3），制品仓已发布 2.13.10/3.8.1/3.16.0

## 验证结果

```bash
$ ./config_loader_test
All tests passed (352 assertions in 29 test cases)   # exit 0
```

## 注意事项

- 纯静态库（header + src/utils/GetFileContent.cpp），产物为 libconfig-loader.a + 头文件
- 三个解析器（JSON/XML/YAML）默认全开，依赖 jsoncpp/tinyxml2/yaml-cpp 均为已发布 Conan 包
- 测试数据文件（configs/）运行时需与二进制同目录（copy_configs 已处理）
---

**编译结束**: 2026-09-25 16:51
**最终状态**: built
