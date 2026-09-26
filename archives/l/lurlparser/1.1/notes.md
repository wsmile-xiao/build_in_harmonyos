# lurlparser 1.1 适配笔记

## 编译环境
- 构建系统: CMake（上游仅 build Example 可执行；补丁 0001 新增 STATIC 库目标与安装规则）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (OHOS aarch64 toolchain)
- 状态: built

## 依赖
- 无第三方运行时依赖（W0 预检通过）
- 上游测试需 gtest/1.17.0（ohpcd 制品仓已发布，W0 conan download 核实）

## 上游测试台账（双口径）
- source_declared_total: 8（test/test.cpp 中 8 个活跃 TEST_F：
  example/cases/ipv6/ipv4/parens/trailingdot/specialchars/escapechars；
  controlchars 为上游注释保留，不计入）
- 关键事实: 上游 tag 内 test.cpp 引用已移除的 clParseURL/m_* 旧 API，
  与 release-1.1 头文件（LUrlParser::ParseURL / scheme_*）不匹配，
  原始 `make tests` 无法编译。补丁 0002 将该 8 用例逐字移植到当前公开 API
  （保持断言语义不变），经 ctest -R lurlparser_tests 实际运行。
- configured_executable_total: 8（1 个 gtest 二进制，注册 8 用例）
- executed_passed_total: 8（8/8 = 100%，见 reports/）

## 遇到的问题与解决方案
1. 上游 CMakeLists 无库目标/安装规则 → 补丁 0001 添加 add_library(STATIC)
   + install 规则 + WITH_TESTS 选项（gtest 经 Conan CMakeDeps 接入）
2. 上游 test.cpp 旧 API 无法编译 → 补丁 0002 移植到 release-1.1 API
3. CMake 4.1.2 与上游 cmake_minimum_required(3.0) 冲突 → 注入
   CMAKE_POLICY_VERSION_MINIMUM=3.5（同仓库先例 edlib 方案）
4. CMake 不识别 OHOS → 注入 CMAKE_SYSTEM_NAME=Linux + armv8（E092）

## 验证结果
- conan create（OHOS aarch64 profile）通过，产物 lib/libLUrlParser.a + include/LUrlParser.h
- 上游 8 个 gtest 用例全部通过（8/8）
- 消费者 test_package: test_lurlparser + test_lurlparser_ohos 均通过

## 消费者用例
- test_package/test.cpp: 经公开头/API 解析完整 URL（user:password/port/query/fragment）
  核验全部字段 + getPort
- test_package/ohos_test.cpp: -Werror 严格编译 + IPv6 主机名 + 端口边界 + authority-only
---

**编译结束**: 2026-09-22 22:09
**最终状态**: built
