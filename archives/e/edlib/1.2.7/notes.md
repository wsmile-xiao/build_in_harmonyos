# edlib 1.2.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (OHOS aarch64, clang 15.0.4 + libc++)
- 状态: published

## 编译步骤

1. 官方源码：https://github.com/Martinsos/edlib tag v1.2.7
   tarball SHA-256: 8767bc1b04a1a67282d57662e5702c4908996e96b1753b5520921ff189974621
2. 本地获取走 ghfast.top 镜像（GitHub 直连超时；conan-verify E017 同款镜像），
   与官方 tarball 文件清单 130 项完全一致，git tree hash e542ad433cf88b5b96ed974ddc5be605e6a0ae04
3. 独立 CMake 编译验证（E092 平台注入）：
   cmake -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=armv8 \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
         -DCMAKE_CXX_FLAGS=-stdlib=libc++ && make && make install DESTDIR=...
4. ctest 全量 1/1 通过；runTests 19/19 独立用例通过（100%）
5. conan-init 生成配方；conan-verify 8 道门禁全 PASS（G0-G4 + L2/L4/L5）
6. finish（W2 结构 + R36 依赖 + W3 本地 CI）：W3 L0/L1 PASS，.ci-result.json exit_code=0
7. 消费者验证：test_package/harmonyos_test.cpp 16 项断言 ALL PASS（conan create 内执行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 拒绝 cmake_minimum_required(3.2) | CMake 4.x 移除 <3.5 兼容（E103/E187/DRAFT-E321） | conanfile.py generate() 用 tc.cache_variables 注入 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | CMake 不识别 OHOS 平台 | CMake 无 HarmonyOS platform module（E092） | 注入 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=armv8 |
| 3 | conan-verify E017 镜像注入残留 .ghfast-bak | conan_verify.py 恢复内容不清理 bak（DRAFT-E323） | 每次 finish 前删除 .ghfast-bak/.orig，恢复官方 URL 再验证 |
| 4 | lang-preflight 误判 python | bindings/python/setup.py 使全树文件名命中 python 分支 | 人工按边界规则复核判 cpp；根因在框架 lang_detect.py，仅记录不改（证据 03_lang_preflight_misjudge.txt） |

## 源码修改

无补丁（patches: {}）。仅配方层注入构建参数，不改上游源码。

## 依赖版本

无外部依赖（零依赖库，requirements 为空）。

## 验证结果

- ctest: 1/1 passed（edlib_tests）
- 上游 runTests: 19/19 独立用例通过（100%）
- HarmonyOS 专项测试 harmonyos_test.cpp: 16 项断言 ALL PASS，退出码 0
- conan create: G2 PASS（含 test_package 消费者验证 1/1）
- W3 本地 CI: L0/L1 pass，.ci-result.json exit_code=0

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（CMakeToolchain + cache_variables 兼容注入） |
| conandata.yml | 官方 URL + SHA-256 |
| test_package/harmonyos_test.cpp | HarmonyOS 专项测试（16 断言） |
| reports/test-report.md | 上游测试枚举台账（19/19） |
| reports/knowledge-candidate-ledger.md | 知识候选台账与四范围查重 |

## 注意事项

- 路径判定：A（常规基础适配，依赖项）——候选 1/3 复用 E103/E187/E092，候选 2 复用 DRAFT-E323，候选 4 根因在框架只记录不修改
- PR 前缀：【依赖项】
- 上游 CMakeLists project 版本写死 1.2.6（上游代码如此），不影响 1.2.7 打包
---

**编译结束**: 2026-09-03
**最终状态**: published
