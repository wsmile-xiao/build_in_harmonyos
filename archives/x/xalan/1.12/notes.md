# xalan 1.12 适配笔记

## 上游与版本
- 上游：Apache Xalan-C++ 1.12.0（tag `Xalan-C_1_12_0`，2020-06-07 发布）
- 官方源：`https://github.com/apache/xalan-c/archive/refs/tags/Xalan-C_1_12_0.tar.gz`
- sha256：`f3d4f23af7f7914259f2f5dbd9cc1450d3ebe0b8c8163fd50fcac4a39c63fccd`（与 conan-center-index 1.12.0 条目一致）
- License：Apache-2.0
- 构建系统：CMake（`cmake_minimum_required(VERSION 3.2.0)`，默认 C++14）
- 本仓版本按任务命名为 `1.12`（对应上游 1.12.0）

## 依赖
- 唯一依赖：`xerces-c/3.2.5`（本仓已适配版本；Xalan 1.12 首选 3.2.3，3.2.x 线兼容）
- `transitive_headers + transitive_libs`：Xerces 头文件泄漏进本库公共头（XercesParserLiaison），必须传递

## 平台与后端选择
- Xalan 的平台检测走通用 UNIX/Threads 标志，无 `STREQUAL "Linux"` 专属分支，`CMAKE_SYSTEM_NAME=HarmonyOS` 下行为一致
- `transcoder=default`（与 conan-center 一致）：ICU 未在本仓发布，不引入 ICU
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`：1.12 时代 CMakeLists（最低 3.2）在 CMake 4 下配置的兼容地板（E103）
- `BUILD_SHARED_LIBS` 必须经 `tc.cache_variables` 设置：上游把它当 CACHE 变量覆盖，普通 variables 会输

## 源码修改（2 个补丁）
| 补丁 | 内容 | 原因 |
|------|------|------|
| `0001-xercesc-target-compat.patch` | `cmake/XalanXerces.cmake`：`find_package(XercesC)` QUIET 化，找不到时回退 `find_package(xerces-c)` 并 `ALIAS XercesC::XercesC` | CCI 的 xerces-c 导出大写 `XercesC::XercesC`，本仓导出小写 `xerces-c::xerces-c`（libe57format 同坑）；fallback 双兼容，无平台宏 |
| `0002-fix-gcc15-encoding-writer.patch` | `XalanOtherEncodingWriter.hpp`：`this->m_isPresentable` → `m_predicate`，`writeNumberedEntityReference` → `writeNumericCharacterReference` | 上游 gcc-15 两阶段查找修复（Fedora/Arch/Debian 同款），clang 15 同样更严；纯 C++ 兼容修复 |

## 上游测试（21 个 ctest，全部保留运行）
- 顶层 `enable_testing()`，`Tests/` 注册 1 个（Threads），`samples/` 注册 20 个（8 通用 + SerializeNodeSet + 2 SimpleXPathAPI + 4 TraceListen + TransformToXercesDOM + UseStylesheetParam + XalanTransform + XalanTransformerCallback + SimpleXPathCAPI）
- `TestXSLT`/`TestXPath` 只构建可执行文件，不注册 `add_test`
- 与 conan-center 差异：CCI 用 `0001-do-not-build-tests-and-samples.patch` 把四目录删掉；本配方不删，`build()` 末尾 `cmake.test()` 全量运行（TEST_QUALITY_SPEC 层 1）
- 计数方式：从 `CTestTestfile.cmake` 数 `add_test(`，失败回退 21（已审计值）；`cmake.test()` 失败即抛异常，走到发射标记即全部通过

## test_package（消费者视角，6 断言）
- `test.cpp`：写 `xalan_test_in.xml` + `xalan_test.xsl` 到工作目录，`XalanTransformer::transform()` 到 `xalan_test_out.xml`，读回断言：返回码 0、输出非空、含 Hello/World/Foo/greeting 共 6 项
- `conanfile.py test()`：跑二进制（非 0 即失败），发射 `HMBS_TEST_PACKAGE_RESULT(discovered 6/passedCount 6)`，并从包内 `res/hmbs_upstream.json` 重放 `HMBS_UPSTREAM_TEST_RESULT`（cache-hit 轮仍有证据）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(XercesC)` 找不到本仓 xerces-c | 本仓目标小写，CCI 大写 | 0001 fallback + ALIAS 双兼容 |
| 2 | `XalanOtherEncodingWriter.hpp` 在新编译器下报错 | 依赖基类成员的两阶段查找 + 改名 API | 0002 回 port 上游 gcc-15 修复 |
| 3 | CMake 4 下老 `cmake_minimum_required(3.2)` 配置失败 | E103 | `CMAKE_POLICY_VERSION_MINIMUM=3.5` |

## 依赖版本
- xerces-c/3.2.5（本仓）
- 工具链：OHOS SDK clang 15，libc++，musl

## 验证结果
- 待 HMBS 真机预检：`conan create`（库构建 + 21 ctest + test_package 6 断言）
- 本轮仅完成未提交工作树，不提前填通过率数字

## 注意事项
- `Xalan` 可执行文件（XSLT 命令行）随库一起构建安装，属库附带工具，不单独声明 commands.json（库类型）
- 静态默认（`shared=False`）：规避 OHOS 共享库 SONAME/签名链路，与 xerces-c 本仓一致
