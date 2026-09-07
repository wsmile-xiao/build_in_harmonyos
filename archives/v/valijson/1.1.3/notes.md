# valijson 1.1.3 适配笔记

## 编译环境
- 构建系统: cmake（INTERFACE header-only 库，无需编译源码）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4（OHOS aarch64 工具链）
- 状态: published

## 编译步骤

```bash
# 1. 下载官方源码并核验
curl -fsSL -o valijson-1.1.3.tar.gz https://github.com/tristanpenman/valijson/archive/refs/tags/v1.1.3.tar.gz
sha256sum valijson-1.1.3.tar.gz   # 887b53b1a924f6fe0b35fa3bbc9bbbe5ae8c72097b7f0f7c17b45f4cfa646029

# 2. conan 配方验证（含 test_package 消费者编译运行）
python3 scripts/ohc-run.py conan-verify valijson 1.1.3   # G0-G4/L2/L4/L5 全通过

# 3. 上游测试套件（钉定 submodule 版本，与上游 CI 一致）
cmake -S . -B build-ohos -Dvalijson_BUILD_TESTS=ON -Dvalijson_EXCLUDE_BOOST=ON \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64
cmake --build build-ohos -j2
./test_suite   # 187 tests / 185 PASS / 2 SKIP（上游自禁）/ 0 FAIL

# 4. 鸿蒙专项测试
clang++ -std=c++17 test_valijson_ohos.cpp -I include -I thirdparty/rapidjson/include && ./test_valijson_ohos
# ALL PASS（double 解析回退路径 + RapidJson 适配器端到端校验）

# 5. finish（W2 原子性 + W3 本地 CI 模拟）
python3 scripts/ohc-run.py finish valijson 1.1.3 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 1.1.1 曾因 OHOS libcxx 缺浮点 from_chars 需补丁替换 strtod | 上游直接使用 std::from_chars(double) | 1.1.3 已内置 internal/double_parser.hpp 自动检测（VALIJSON_HAS_STD_FROM_CHARS=0 → istringstream 回退），实测解析正确，无需补丁 |
| 2 | CMake 不识别 OHOS 平台（E092） | CMake 无 HarmonyOS platform module | generate() 设 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 3 | W3 本地 CI 的 JC5 误报他库 .ci-trigger | main 基线已跟踪 util-linux-login 隐藏文件，本分支无提交时 junk_check 回退 full 模式 | 提交本库变更后增量模式只检本库文件，JC 通过 |

## 源码修改

无（1.1.3 为 header-only，且上游已修复 from_chars 回退；无补丁）

## 依赖版本

无运行时依赖（header-only）；测试期可选依赖 Boost/Poco/Qt 未启用（互斥编译分支，见 test-report.md 台账）

## 验证结果

```bash
# 上游测试
./test_suite          # [==========] 187 tests from 22 test suites ran. PASSED 185, SKIPPED 2, FAILED 0, rc=0
# 鸿蒙专项测试
./test_valijson_ohos  # ALL PASS, rc=0
# conan 消费者测试
conan create ...      # test_package: ./test_valijson PASS, rc=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| packaging/valijson-1.1.3-ohos-aarch64.tar.gz | 发布产物（头文件 + CMake 配置） |
| packaging/valijson-1.1.3-debug.tar.gz | debug 产物 |
| reports/conan-verify-report.md | conan 验证报告 |
| reports/test-report.md | 上游测试双口径台账 |

## 注意事项

- valijson 为 INTERFACE header-only 库，package_info().libs 为空（无需链接）。
- StdStringAdapter 持有 const std::string& 引用，使用时必须绑定生存期更长的命名对象（API 契约）。
- thirdparty 子模块按 v1.1.3 钉定 commit 还原，测试数据与上游 CI 一致。

### 对话 #valijson-1.1.3-r01-pc3-8-20260904T192801Z

- pc3-8 执行端完成 valijson 1.1.3 第一轮完整适配：环境核验、源码 SHA-256 核验、上游测试全量枚举与运行、鸿蒙专项测试、conan 配方与 test_package、W2/W3 门禁全部通过。
- 路径判断：见知识候选台账与七轴查重（reports/ 与最终回传）。

**编译结束**: 2026-09-05
**最终状态**: published
---

**编译结束**: 2026-09-05 05:06
**最终状态**: published
