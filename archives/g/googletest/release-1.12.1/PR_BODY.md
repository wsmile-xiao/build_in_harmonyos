- **三方库名称**：googletest（GoogleTest + GoogleMock）
- **上游版本**：release-1.12.1（上游 tag；框架内部 GOOGLETEST_VERSION=1.12.1）
- **上游仓库地址**：https://github.com/google/googletest
- **适配路径**：路径 A（基础适配）
- **使用知识库**：适配共性问题与首次真机启动避坑指南（lerc/glfw 式 OHOS cmake 适配模式）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 74 个自测源文件 / ~50 个自测二进制 | 上游**框架自测套件**：`googletest/test/*.cc` 52 个 + `googlemock/test/*.cc` 22 个源文件，开启 `gtest_build_tests=ON` + `gmock_build_tests=ON` 会构建约 50 个自测二进制（gtest_unittest / gmock_test / googletest-death-test-test / 各 python 驱动可执行 等） |
| 集成测试 | 0 | 上游无独立集成测试套件 |
| 其他测试 | 0 | 框架自测之外无其他可执行测试 |
| **合计** | **74 源 / ~50 二进制 / 数千断言** | |

> **rule4 整改说明（本 PR 已在 CI 真机实跑上游框架自测）**：`conanfile.py` build() 中 OHOS 构建
> `-Dgtest_build_tests=ON -Dgmock_build_tests=ON`，并把其中**可在 OHOS 真机实跑的「纯逻辑」自测二进制
> 29 个全部纳入**：逐一 `cmake --build <target>` → binary-sign-tool 自签 → 真机实跑，
> 任一未构建/未 rc=0 即 raise（严格门禁，CI 显红取证）。
> 实跑结果见「验证结果」，未运行二进制逐条 1-e 技术原因见「未运行项说明」。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 4 断言 | 新增 | `test_package/test.cpp`：3 个 gtest `TEST`（整数/字符串断言）+ 1 个 gmock `EXPECT_CALL` mock 调用断言，链接打包的 `libgmock.a`/`libgtest_main.a`/`libgtest.a` 在真机实跑 |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 0 | 不变 | 消费者测试即鸿蒙特有验证；上游自测实跑见 build() 严格门禁 |
| **合计** | **4** | **+4** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（仅用 `--gtest_filter` 在运行时排除 1-e 类不可执行用例，不改上游源码）
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：新增 1 个 Conan consumer smoke test（`test_package/test.cpp`），在真机用 clang++ 静态链接打包的 `libgmock.a`/`libgtest_main.a`/`libgtest.a` 与 `-lpthread` 编译运行，包含 3 个 gtest `TEST` 用例（`EXPECT_EQ(2+2,4)`、`EXPECT_GT`、`EXPECT_STREQ`）和 1 个 gmock 用例（`MOCK_METHOD` + `EXPECT_CALL(m.add(2,3)).WillOnce(Return(5))`），断言全过，输出 `[ PASSED ] 4 tests`。
- **补全原因**：证明打包的四个静态库（gtest/gtest_main/gmock）在 OHOS 上可编译链接、可运行、断言与 mock 行为正确；同时验证静态链接顺序（gmock_main → gmock → gtest_main → gtest）正确。
- **新增测试文件清单**：
  1. `archives/g/googletest/release-1.12.1/test_package/test.cpp` — gtest+gmock 消费者测试（4 断言）

## 验证结果

- 编译状态：通过（GitCode CI 真机 **build #37414**，`conan-build-test` ✅ / L0+L1 门禁 ✅ / 全步骤 ✅）
- 上游测试用例通过率（实跑子集，CI 真机 OHOS aarch64/musl）：
  - **29/29 个可实跑自测二进制**全部构建 + 自签 + 真机实跑，**rc=0 全通过**（严格门禁：历次显红 build #37394/#37407 均已收敛，最终 #37414 全绿）
  - 实跑框架用例 **`[ PASSED ] 1706/1706`**；另有 `gtest_skip_test` 3 用例按 GTEST_SKIP 设计全部 **SKIPPED**（rc=0）、`gtest_no_test_unittest` 0 用例验证「无测试程序可运行」路径
  - 未运行的其余 ~20 个上游二进制为 **1-e 类技术豁免**，逐条见下「未运行项说明」（death/fork、python 驱动、/tmp 流捕获、非默认编译变体、负向/压力）
- 新增测试用例通过率：4/4（100%），`test_package` 由 GitCode CI 真机实跑（`test_probe` 输出 `[  PASSED  ] 4 tests.`）

### 实跑上游自测二进制逐项结果（CI 真机）

googletest（19 个）：

| 自测二进制 | PASSED | 说明 |
|-----------|--------|------|
| gtest_unittest | 373 | 核心单测（排除 ParseFlags/Flagfile/TestResultProperty 等 /tmp、death 依赖用例） |
| googletest-printers-test | 145 | 打印器 |
| gtest_pred_impl_unittest | 160 | EXPECT_PRED 谓词宏 |
| googletest-param-test-test | 86 | 参数化测试 |
| googletest-filepath-test | 57 | FilePath 工具类 |
| gtest-typed-test_test | 47 | 类型参数化 TYPED_TEST |
| googletest-port-test | 42 | 平台抽象层（排除 CaptureTest 流捕获） |
| googletest-message-test | 17 | 流式断言消息 |
| googletest-test-part-test | 14 | TestPartResult |
| googletest-options-test | 12 | flag 选项解析 |
| gtest-unittest-api_test | 4 | 测试注册 API |
| googletest-listener-test | 2 | TestEventListener |
| gtest_prod_test | 2 | FRIEND_TEST |
| gtest_sole_header_test | 2 | 单头文件自包含 |
| gtest_environment_test | 1 | 全局 SetUp/TearDown |
| gtest_main_unittest | 1 | gtest_main 入口 |
| gtest_skip_in_environment_setup_test | 1 | 环境 SetUp 中 GTEST_SKIP |
| gtest_skip_test | 0(+3 SKIPPED) | GTEST_SKIP 跳转特性自测（3 用例按设计全部 SKIPPED，rc=0） |
| gtest_no_test_unittest | 0 | 「无测试程序可运行」路径验证（rc=0 即通过） |

googlemock（10 个）：

| 自测二进制 | PASSED | 说明 |
|-----------|--------|------|
| gmock-matchers-comparisons_test | 172 | 比较匹配器 |
| gmock-matchers-misc_test | 144 | 杂项匹配器 |
| gmock-more-actions_test | 110 | 附加 Action |
| gmock-matchers-arithmetic_test | 100 | 算术匹配器 |
| gmock_link_test | 96 | 模板链接/实例化 |
| gmock-function-mocker_test | 76 | MOCK_METHOD 函数模拟器 |
| gmock-cardinalities_test | 27 | 调用次数约束 |
| gmock_test | 13 | gmock 核心行为 |
| gmock_ex_test | 1 | 使用示例冒烟 |
| gmock-port_test | 1 | 平台适配层 |

> 小计：googletest 966 + googlemock 740 = **1706 PASSED**；另 3 SKIPPED（gtest_skip_test）、1 个 0 用例验证程序（gtest_no_test_unittest）。完整逐行日志见 CI build #37414 的 `[gtest-self-test]` 输出（29/29 PASS、`passed_tests=1706`）。

### 未运行项说明（1-e 类技术豁免，逐条）

| 上游自测二进制 | 未运行原因（1-e） |
|---------------|-------------------|
| googletest-death-test-test | death-test 套件，依赖 fork 子进程；OHOS musl fork 受限（#7742 brpc 先例豁免） |
| gtest-death-test_ex_nocatch_test / gtest-death-test_ex_catch_test | death-test + 异常变体，同上 fork 依赖 |
| gtest_repeat_test | --gtest_repeat 硬计数 death-test 执行次数，过滤后自相矛盾（实测 rc=-6） |
| gtest_premature_exit_test | 需 fork 子进程提前 exit 验证 premature-exit 路径 |
| gtest_throw_on_failure_ex_test | 负向用例：故意抛异常/断言失败路径，需宿主进程能力 |
| gtest_stress_test | 压力测试，需长时间长跑 + 宿主资源 |
| gtest_no_rtti_unittest / gmock_no_rtti_test / gmock-more-actions_no_exception_test | 非默认编译变体冒烟（-fno-rtti/-fno-exceptions），非交付配置 |
| gtest_dll_test_ / gtest_all_test(shared) | 共享库(dll)形态冒烟；OHOS 交付为静态库 |
| googletest-break-on-failure-unittest_ / googletest-catch-exceptions-{no-ex,ex}-test_ / googletest-color-test_ / googletest-env-var-test_ / googletest-filter-unittest_ / gtest_help_test_ / googletest-list-tests-unittest_ / googletest-output-test_ / googletest-shuffle-test_ / googletest-throw-on-failure-test_ / googletest-uninitialized-test_ / gtest_list_output_unittest_ / gtest_xml_outfile{1,2}_test_ / gmock_output_test / gmock_leak_test | python(py_test) 驱动：需宿主 python 3 驱动子进程并对 stdout/stderr/XML/JSON/golden 做比对，多数依赖可写 /tmp 捕获输出（OHOS 应用沙箱不可写 /tmp）；部分为故意崩溃的负向用例 |
| gmock-actions_test / gmock-matchers-containers_test / gmock-internal-utils_test / gmock-spec-builders_test / gmock-nice-strict_test | 内嵌 EXPECT_DEATH/ASSERT_DEATH/异常路径用例（实测 1~9 处，如 AssertTest.FailsFatallyOnFalse、OnCallSyntaxTest.WillByDefaultIsMandatory、NiceMockTest.ThrowsExceptionForUnknownReturnTypes），OHOS musl 无 fork 无法执行；其纯逻辑 mock 行为已由同批 gmock-function-mocker/gmock-matchers-*/gmock_link/gmock-cardinalities 等 10 个 gmock 二进制覆盖实跑 |

> death-test/fork 类豁免依据与 #7742（brpc 适配 googletest death test 的 musl fork 说明）一致；/tmp 限制为 OHOS 应用沙箱实测结论（gtest-port.cc 硬编码 `mkstemp("/tmp/gtest_captured_stream.XXXXXX")`，无写权限即 GTEST_LOG_(FATAL) SIGABRT）。

## 补充说明

- 本 PR 只新增 `archives/g/googletest/release-1.12.1/` 下的 googletest 配方、元数据、README 与 test_package，不修改其他目录。
- 包名 `googletest/release-1.12.1`，目录 `archives/g/googletest/release-1.12.1/`；分支 `feat/googletest-release-1.12.1` 与任务分支一致。
- 构建沿用 lerc/glfw 已验证模式：`_ohos_toolchain()` 自发现 ohos.toolchain.cmake（`OHOS_NDK_HOME` 或 `/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake`），裸 `cmake -B -DCMAKE_TOOLCHAIN_FILE=... -DOHOS_ARCH=arm64-v8a -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_SHARED_LIBS=OFF -DINSTALL_GTEST=ON -DBUILD_GMOCK=ON -Dgtest_build_tests=ON -Dgmock_build_tests=ON`，`cmake --install` 安装四静态库 + 头文件 + GTestConfig.cmake + pkg-config。
- OHOS 自测二进制运行前逐一 `binary-sign-tool sign -selfSign` 自签（与 cdecode/mbw 消费者同法）；纯静态库产物（`.a`）本身无需签名。
- E012 修复：ohos.toolchain.cmake 把 CMAKE_AR 覆写为 bare name（llvm-ar）不在 PATH 中，用 `_ohos_llvm_bin()` 推导 LLVM bin 绝对路径并覆写最高优先级 CMAKE_AR/RANLIB/CREATE_STATIC_LIBRARY 规则（与 draco/1.5.7 同法）。
- 源码 tarball 来自 GitHub 上游 tag `release-1.12.1`，sha256 `81964fe578e9bd7c94dfdb09c8e4d6e6759e19967e397dbea48d1c10e45d0df2` 已与解包目录校验一致。
