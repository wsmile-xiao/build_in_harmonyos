- **三方库名称**：googletest
- **上游版本**：1.17.0
- **上游仓库地址**：https://github.com/google/googletest
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（gtest/1.17.0.1 同源码配方先例、googletest/1.12.1 包名形态+GTest 桥接先例、glib2/scnlib test_package 运行环境先例）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 63 | 上游 CMake 注册的 63 个测试目标（ctest -N 实测：googletest 侧 45 = 24 cxx_test + 3 cxx_test_with_flags + 18 py_test；googlemock 侧 18 = 15 cxx_test + 1 gmock_stress_test + 2 cxx_test_with_flags） |
| **合计** | **63** | BUILD_GMOCK=ON 默认形态 add_test 注册数实测；gmock 侧 2 个 py_test（gmock_leak/gmock_output）因 find_package(Python3) 在 gtest 子目录作用域执行不上传父作用域，上游默认形态即不注册 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 63 | 不变 | 上游测试套件全量纳入构建（gtest_build_tests + gmock_build_tests=ON），OHOS PC 真机实跑 63/63 全部通过（100%） |
| 消费者测试 | 1 | +1 | find_package(GTest) + 链接 GTest::gtest_main 与 GTest::gmock，3 个 TEST 用例（断言/匹配器/MOCK_METHOD 模拟对象） |
| **合计** | **64** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，仅平台判定/临时目录等 portability 修正，测试逻辑与断言不变：

> 1. `patches/0001-tmpdir-ohos-sandbox.patch` — gtest-port.cc mkstemp 临时目录改为读 TMPDIR（OHOS 沙箱 /tmp 只读；否则死亡测试/流捕获测试无法运行）。仅改测试支撑基础设施的临时目录来源，测试逻辑不变。
> 2. `patches/0002-gtest-help-ohos-platform-detect.patch` — gtest_help_test.py 的 IS_LINUX 平台判定将 HarmonyOS 归入 Linux 族（uname[0]='HarmonyOS' 误判 False 错走 assertNotIn 分支）。断言逻辑不变，仅平台族归属修正。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游已有完整测试套件，适配后补充了消费者测试

> - **补全的测试范围**：新增 1 个消费者测试（test_package/test.cpp：3 个 TEST 用例）
> - **补全原因**：验证 GTest::gtest_main / GTest::gmock 组件与 GTestConfig.cmake 桥接在 OHOS 上可链接可用（与下游 scnlib 的 find_package(GTest CONFIG REQUIRED) 消费形态完全一致）
> - **新增测试文件清单**：
>   1. `archives/g/googletest/1.17.0/test_package/test.cpp` — 3 个 TEST 用例验证

## 验证结果

- 编译状态：通过（本地 conan create 全流程通过，4 个静态库产物完整）
- 上游测试执行情况：上游 CMake 注册的 **63 个测试目标全部构建并实跑**，OHOS PC 真机（HarmonyOS aarch64）`ctest` 实测：
  - **63/63 全部通过（100%）**：47 个 C++ 测试二进制直接运行通过 + 16 个 Python 驱动测试（py_test，官方 unittest runner）通过
  - 通过前提：patch 0001（TMPDIR 临时目录）+ patch 0002（gtest_help_test 平台判定）
- 上游测试用例通过率：**63/63（100%）**
- 新增测试用例通过率：1/1（100%，test_package 3 个 TEST 用例通过）

## 补充说明

- **构建方式**：CMake 标准构建，C++17
- **包名形态**：googletest（上游原生名）。与仓内 gtest/1.17.0（conan 惯用名）同源码同 sha256，本包为下游 find_package(GTest)/FetchContent(googletest) 形态消费者提供 googletest 原生包名依赖（平台任务 #7344，解锁 scnlib #9694 上游测试依赖）
- **CMakeDeps 桥接**：recipe cmake_file_name="GTest" 生成 GTestConfig.cmake；components 桥接 GTest::gtest / GTest::gtest_main / GTest::gmock / GTest::gmock_main（与上游 install 导出一致，googletest/1.12.1 先例同款）；包内含上游原生 lib/cmake/GTest/GTestConfig.cmake 双保险
- **产物**：4 个静态库（libgtest.a、libgtest_main.a、libgmock.a、libgmock_main.a）
- **依赖**：无外部 Conan 依赖
