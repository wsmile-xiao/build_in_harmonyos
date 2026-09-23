# embedded-cli 0.1.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4（OHOS arm64 工具链）
- 状态: built

## 编译步骤

```bash
# Bootstrap: init-build 从官方 GitHub tag v0.1.4 下载源码
python3 scripts/ohc-run.py init-build embedded-cli 0.1.4 \
  --url=https://codeload.github.com/funbiscuit/embedded-cli/tar.gz/refs/tags/v0.1.4
# 语言预检
python3 scripts/ohc-run.py lang-preflight embedded-cli 0.1.4 --src $BUILD_SRC_DIR
# 生成并验证配方
python3 scripts/ohc-run.py conan-init embedded-cli 0.1.4
python3 scripts/ohc-run.py conan-verify embedded-cli 0.1.4
```

- 配方: conanfile.py 使用 CMakeToolchain/CMake（库为 CMake 构建，非 autotools）。
  conan create 经 ohos-aarch64 profile 干净构建，G1-G4/L2/L4/L5 全过。
- 上游测试: `cmake -DBUILD_TESTS=ON .. && make && ctest`（Catch2 子模块按
  上游 pin commit c837cb4a8aaa 拉取填充 deps/catch2）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create source() 报 BadZipFile | conandata.yml 的 codeload URL 以 `/v0.1.4` 结尾无扩展名，Conan get() 按 zip 解压 | conandata.yml 增加 `filename: embedded-cli-0.1.4.tar.gz` |
| 2 | test_package find_package 找不到 embedded_cli_lib | 上游 add_subdirectory(lib) 使静态库位于 build 目录 lib/ 子目录，package() 顶层 copy 漏包 | package() 显式定位 build_folder/lib/libembedded_cli_lib.a |
| 3 | 消费者测试 binding 回调未触发 | embeddedCliProcess() 在 writeChar==NULL 时直接返回，rx 缓冲永不处理 | 测试设置 sink writeChar 回调 |
| 4 | tokenizeArgs=true 时参数串为 tokenize 格式 | token 间以 0x00 分隔，snprintf 只取到首 token | 用公开 API embeddedCliGetToken 读取并断言 |

## 依赖版本

- Catch2: 上游子模块 pin commit c837cb4a8aaa（deps/catch2），registry 存在
  catch2/2.13.10-r0、2.13.10、3.8.1、3.16.0（R35 用 conan list 查询可用性，
  测试构建实际使用钉定源码，非 registry 二进制）。

## 上游测试双口径台账（R51 完整枚举）

### 源码声明枚举（source_declared_total = 9）

| 测试源文件 | TEST_CASE | 分类理由 | 是否独立用例 |
|-----------|-----------|----------|-------------|
| tests/TokensTest.cpp | "EmbeddedCli. Tokens" | 用户测试源独立 TEST_CASE | 是 |
| tests/cli/AutocompleteTest.cpp | "CLI. Autocomplete enabled" | 用户测试源独立 TEST_CASE | 是 |
| tests/cli/AutocompleteTest.cpp | "CLI. Autocomplete disabled" | 用户测试源独立 TEST_CASE | 是 |
| tests/cli/BaseTest.cpp | "CLI. Base tests" | 用户测试源独立 TEST_CASE | 是 |
| tests/cli/BaseTest.cpp | "CLI. Changed invitation" | 用户测试源独立 TEST_CASE | 是 |
| tests/cli/HelpTest.cpp | "CLI. Help" | 用户测试源独立 TEST_CASE | 是 |
| tests/cli/HistoryTest.cpp | "CLI. History" | 用户测试源独立 TEST_CASE | 是 |
| tests/cli/PrintTest.cpp | "CLI. Printing" | 用户测试源独立 TEST_CASE | 是 |
| tests/cli/StaticAllocationTest.cpp | "CLI. Static allocation" | 用户测试源独立 TEST_CASE | 是 |

框架文件（deps/catch2/*）、辅助源（CliBuilder.cpp/CliWrapper.cpp，非用例仅支撑）、
examples/ 样例不计入独立用例，仅作为台账列示。

### 配置实例化（configured_executable_total = 1）

- 构建目标: `embedded_cli_tests`（tests/CMakeLists.txt，Catch2WithMain 链接，
  BUILD_TESTS=ON 时实例化；BUILD_SINGLE_HEADER=OFF 时链接 EmbeddedCLI::EmbeddedCLI）
- ctest 注册: `add_test(CliTests tests/embedded_cli_tests)` → ctest 1 项

### 执行结果

- ctest: `1/1 Test #1: CliTests Passed`，exit 0
- 二进制直跑: `All tests passed (541 assertions in 9 test cases)`
- executed_passed_total = 1（ctest 项）/ 9（TEST_CASE 全过）
- 失败数 = 0；未运行/未实例化 = 0

### 逐项映射

| 源码声明/宏 | 预处理/构建条件 | 构建目标 | ctest 注册 | 实际执行 |
|------------|----------------|----------|-----------|---------|
| 9 个 TEST_CASE | `if(BUILD_TESTS)` enable_language(CXX)+CTest；deps/catch2 子模块钉定源码 | embedded_cli_tests | CliTests | 全部通过（541 断言） |

### 统计口径

- 全量通过率（按发现总数）: 9/9 = 100%（541 断言全过）
- 当前配置可执行集合通过率: 9/9 = 100%（同一二进制，无互斥分支未实例化项）

## 验证结果

```bash
$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 1
$ ./tests/embedded_cli_tests
All tests passed (541 assertions in 9 test cases)
```

## 注意事项

- 上游单头文件 CLI 库（C，静态库 embedded_cli_lib），纯库包，无 CLI 可执行产物，
  不创建 commands.json（R38 仅 CLI 包需要）。
- 上游处于维护模式（README 提示重写为 embedded-cli-rs），无构建期外部依赖。

## 知识候选台账（knowledge_candidate_ledger）

### 候选 K1: Conan get() 对无扩展名 codeload URL 误判 zip（BadZipFile）
- 真实错误: `conan create` source() 报 `BadZipFile: File is not a zip file`，
  codeload URL `.../tar.gz/refs/tags/v0.1.4` basename 为 `v0.1.4` 无扩展名。
- 根因: `get()` 按 URL basename 推断压缩格式，无扩展名默认按 zip 解压。
- 修复: conandata.yml `sources.filename: "embedded-cli-0.1.4.tar.gz"`（不依赖
  conanfile.py 修改，conandata 单行字段即修复），URL 保持官方源不变。
- 验证: conan-verify G2 通过，G1-G4/L2/L4/L5 全过。
- 适用范围: 任何使用 codeload/无扩展名 tag URL 的 conan 配方。
- 查重: 正式知识 E276（get() filename= 参数方案）、E483（explicit-filename-in-get）、
  E392 命中同类根因 → **exact_duplicate/causal_duplicate = true**，
  trigger_overlap/solution_overlap = true（本候选用 conandata filename 字段，
  与 E276/E483 的 conanfile.py get(filename=) 属同一修复原理的两种落点）。
  combination_novelty/boundary_novelty/test_migration_novelty = false。
- 决定: **reuse_existing（复用 E276/E483，不建草稿）**，归属 path_a_no_knowledge。

### 候选 K2: CMake add_subdirectory 静态库产物位于 build 目录子目录，package() 顶层复制漏包
- 真实错误: test_package `find_package(embedded-cli)` 报
  `Library 'embedded_cli_lib' not found in package`。
- 根因: 上游 `add_subdirectory(lib)` 使静态库输出在 CMake binary dir 的
  `lib/` 子目录（`build/clang-15-armv8-17-release/lib/libembedded_cli_lib.a`），
  conan package() 按 build 顶层 glob 复制找不到产物。
- 修复: package() 显式定位 `build_folder/lib/libembedded_cli_lib.a`，未命中时
  `os.walk(build_folder)` 递归兜底复制。
- 验证: conan-verify G2 通过（test_package 2/2 通过）。
- 适用范围: 任何使用 add_subdirectory 布局、产物落子目录的 CMake 库配方。
- 查重: 正式知识 E340（cargo 产物 glob 递归定位）为最接近条目 —— 同属
  "build 目录内产物位置不确定时用 glob/os.walk 递归定位" 的解决原理。
  exact_duplicate = false（E340 场景是 cargo/basic_layout，本候选是 CMake
  add_subdirectory 子目录布局）；causal_duplicate = false；trigger_overlap = true；
  solution_overlap = true（都是递归定位产物）；combination_novelty = true
  （CMake add_subdirectory 子目录布局 + os.walk 兜底的具体组合）；boundary_novelty = true
  （E340 未覆盖 add_subdirectory 子目录场景）；test_migration_novelty = false。
- 决定: **new_draft（路径 B，CMake 静态库子目录产物定位）**，建立
  DRAFT-embedded-cli-0.1.4-cmake-subdir-static-lib-package 草稿。

### 候选 K3: 回调驱动 CLI 库消费者测试需先设置输出回调（embeddedCliProcess 空转）
- 真实错误: 消费者 test 注入命令后 binding 回调未触发。
- 根因: `embeddedCliProcess()` 在 `cli->writeChar == NULL` 时直接 return，
  rx 缓冲永不处理；上游包装类（CliWrapper）在构造时设置 writeChar。
- 修复: 消费者测试在 process 前设置 sink writeChar 回调。
- 验证: 修正后 binding 触发、token 断言通过（conan-verify G2）。
- 适用范围: embedded-cli 消费者/任何有 writeChar 前置条件的回调驱动 CLI 库。
- 查重: 正式知识/图谱/草稿三范围均未命中同类（搜索 writeChar/回调/空指针均无
  覆盖）。exact_duplicate/causal_duplicate/trigger_overlap/solution_overlap/
  combination_novelty/boundary_novelty/test_migration_novelty 七轴均 false
  （无既有条目），新增差异 = 完整新知识。
- 决定: **new_draft（路径 B，embedded-cli 消费者测试 writeChar 前置条件）**，
  与 K4 合并为同一 .md/.kv 草稿（同 stem）。

### 候选 K4: tokenizeArgs=true 回调收到 tokenize 串（0x00 分隔），需用公开 token API 读取
- 真实错误: 回调捕获 args 只得到首个 token（"1"），期望 "1 1"。
- 根因: tokenizeArgs=true 时回调参数是 tokenize 后的字符串（token 间单 0x00、
  结尾双 0x00），snprintf 只读到首 token。
- 修复: 用公开 API `embeddedCliGetToken(args, n)` 逐 token 读取并断言。
- 验证: 修正后断言通过（conan-verify G2）。
- 适用范围: embedded-cli 消费者测试。
- 查重: 三范围均未命中（搜索 tokenize/token 分隔无覆盖）。
  exact_duplicate/causal_duplicate/trigger_overlap/solution_overlap/
  combination_novelty/boundary_novelty/test_migration_novelty 七轴均 false。
- 决定: **new_draft（路径 B）**，与 K3 合并为同一草稿。

### 路径判断总决定
- K1 → reuse_existing（E276/E483）→ path_a_no_knowledge
- K2/K3/K4 → new_draft（路径 B 知识库扩展）→ 建立
  DRAFT-embedded-cli-0.1.4-cmake-subdir-static-lib-package.md/.kv 与
  DRAFT-embedded-cli-0.1.4-consumer-test-callback-tokenize.md/.kv
---

**编译结束**: 2026-09-22 00:40
**最终状态**: built
