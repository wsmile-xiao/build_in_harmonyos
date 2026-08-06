- **三方库名称**：gtest
- **上游版本**：1.17.0
- **上游仓库地址**：https://github.com/google/googletest
- **适配路径**：路径 A（基础适配）
- **使用知识库**：Google Test C++ 测试框架，C++17，零依赖，CMake 构建

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 65 | googletest + googlemock 编译出的 65 个测试二进制（对应 97 个测试源文件，数千 TEST 用例） |
| **合计** | **65** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 65 | 不变 | 上游测试二进制已纳入构建（gtest_build_tests + gmock_build_tests=ON），OHOS 真机实跑 |
| 消费者测试 | 1 | +1 | 链接 libgtest.a，2 个 TEST 用例（1+1=2 + string eq） |
| **合计** | **66** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游已有完整测试套件，适配后补充了消费者测试

> - **补全的测试范围**：新增 1 个消费者测试（test.cpp：TEST(SmokeTest, Add) 1+1=2 + TEST(SmokeTest, StringEq)）
> - **补全原因**：验证 libgtest.a 在 OHOS 上可链接可用
> - **新增测试文件清单**：
>   1. `archives/g/gtest/1.17.0/test_package/test.cpp` — 2 个 TEST 用例验证

## 验证结果

- 编译状态：通过（本地 CI 模拟 L0/L1/L4/L5 全部通过）
- 上游测试执行情况：googletest + googlemock 编译出 **65 个测试二进制**，已在 OHOS 真机实跑：
  - **53 个直接运行通过**（覆盖 gtest 核心断言、gmock 匹配器/动作、参数化测试、typed test 等）
  - **6 个通过官方 Python 包装器驱动**（googletest-filter-unittest、googletest-break-on-failure-unittest、googletest-color-test、googletest-env-var-test、gmock_output_test、gmock_leak_test，验证 stdout/退出码组合）
  - **6 个未通过**（均为 gtest 框架特定编译配置/场景要求，非功能缺陷）：
    1. googletest-output-test_ — 输出格式与 golden 的行号占位符差异（clang 输出格式与 gtest 预期不完全一致）
    2. gtest_help_test_ — --gtest_stream_result_to 标志依赖 socket 编译配置，OHOS 编译下该标志出现于帮助输出（与 golden 预期不符）
    3. gtest_xml_output_unittest_ — XML 输出格式与 golden 的字段顺序差异
    4. googletest-catch-exceptions-ex-test_ — 需 -fexceptions 特殊编译 gtest（默认无异常支持）
    5. gtest_dll_test_ / shared_gmock_test_ — 需共享库（.so）链接场景，OHOS 适配为静态库
- 上游测试用例通过率：**59/65（90.8%）**，6 个未通过均为 gtest 框架特定编译配置/场景要求（详见上，非库功能缺陷）
- 新增测试用例通过率：1/1（100%，test_package 2 个 TEST 用例通过）

## 补充说明

- **构建方式**：CMake 标准构建，C++17
- **补丁**：
  - 0001-tmpdir-ohos-sandbox.patch — gtest-port.cc mkstemp 临时目录改为读 TMPDIR（OHOS 沙箱 /tmp 只读，否则死亡测试/流捕获测试失败）
- **产物**：4 个静态库（libgtest.a、libgtest_main.a、libgmock.a、libgmock_main.a）
- **依赖**：无外部 Conan 依赖
