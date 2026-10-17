## PR 信息

- **三方库名称**: trompeloeil（header-only C++ mocking framework）
- **上游版本**: v49（tag；Conan 版本号 `49`）
- **上游仓库地址**: https://github.com/rollbear/trompeloeil
- **前置依赖关系**: 运行时零依赖（header-only，产物仅 `include/` + `licenses/`）；构建期上游自测依赖 `catch2/3.8.1`（作为 `tool_requires`，ohpcd 制品仓已发布）
- **适配路径**: 路径 A（基础适配）+ 路径 B（知识库扩展，见下方「路径 B 知识贡献说明」）
- **使用知识库**: SKILL 铁律 R32/R33/R39/R51（OBS 平台判断 / 编译器来源 / 官方源 URL / 上游测试三步法）；E002（OHOS `/tmp` 只读）；E063（`-Werror` 与警告治理评估）；`DRAFT-11301-ohos-compile-fail-suite` 为本 PR 新增知识草稿（另见关联 issue #3048）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试（Catch2 v3 `self_test`） | 604（C++14 执行）/ 615（C++20 执行） | 来源：`test/compiling_tests.cpp` + `compiling_tests_11.cpp` + `compiling_tests_14.cpp`（C++20 追加 `test_co_mock.cpp` 协程用例）；运行时实跑 1361 / 1394 断言 |
| 负向编译测试（expect-to-fail） | 68 | 来源：`compilation_errors/*.cpp` + `verify_compilation_error.sh`（每用例要求编译失败且诊断匹配声明的 `// pass:` 正则）。C++14 按上游 `// exception:` 规则排除 18 个后执行 50；C++20 全量 68 |
| 其他测试 | 2 | `thread_terror`（多线程调用/返回计数压力）、`custom_recursive_mutex`（自定义递归互斥量适配） |
| **合计** | **674 / 685** | 604+68+2（C++14）/ 615+68+2（C++20） |

> 上游 CI 对 68 个负向用例在每个 C++ 标准上运行一遍（`CXXFLAGS="-std=c++NN" ./check_errors.sh`）；本 PR 在 C++14 与 C++20 两个标准上执行。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 604 / 615 | 不变 | 未修改任何用例；C++14 与 C++20 双标准在 `conan create` 内全量执行（100% 通过） |
| 负向编译测试 | 68 | 不变 | 驱动层替换：OHOS 无 GNU `parallel`，配方用线程池逐用例调用**同一个**未修改的 `verify_compilation_error.sh`，按上游语义（`grep FAIL | wc -l`）计数；C++14 执行 50/50 PASS、C++20 执行 68/68 PASS，0 FAIL |
| 其他测试 | 2 | 不变 | `thread_terror`、`custom_recursive_mutex`（随 C++14 `self_test` 一并构建执行） |
| 鸿蒙特有测试 | 1 个消费者程序（4 用例 / 5 断言） | 新增 | `test_package` Catch2 消费者：`RETURN` 桩值、`gt()` 匹配器 + `TIMES`、`LR_SIDE_EFFECT` 参数观测、`expectation_violation` 违反报告 |
| **合计** | **675 / 686（含消费者程序）** | **+1** | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

`patches: {}`：本 PR 不含任何补丁，未改动上游源码、测试用例、`// pass:` / `// exception:` 正则与驱动脚本。唯一的环境差异处理全部位于 `conanfile.py`：以 `tool_requires catch2/3.8.1` + `-DCMAKE_PREFIX_PATH` 预置测试框架（阻断上游 CMake 构建期下载兜底）、以线程池替代 GNU `parallel` 的 fan-out、`TMPDIR` 固定到构建目录。

## 补全测试用例说明

### 上游是否存在无测试用例、适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（自测 604/615 + 负向 68 + 2 个独立程序全部真实执行）
- [ ] **是**，上游无测试用例，适配后补全了测试

另新增 1 个消费者测试（`test_package/`），用于验证安装包视角的 CMake 目标（`trompeloeil::trompeloeil`）与真实 API 可用性：

1. `archives/t/trompeloeil/49/test_package/test_trompeloeil.cpp` — 定义 mock、设置期望、调用并断言（含违反报告路径）
2. `archives/t/trompeloeil/49/test_package/CMakeLists.txt`
3. `archives/t/trompeloeil/49/test_package/conanfile.py`
4. `archives/t/trompeloeil/49/test_package/MANIFEST.yml`

## 验证结果

### 编译验证

- 编译器: OHOS SDK clang/clang++ 15.0.4（aarch64-linux-ohos），libc++ 15
- 编译状态: **通过**（`conan create` G2 PASS；`.ci-result.json` `exit_code=0`）
- 构建系统: CMake ≥ 3.14（上游；配方以 CMake 驱动构建上游自测）
- Profile: `ohos-aarch64`（CI）/ `ohos-aarch64-device`（本机验证）

### 测试通过率（真机实测）

| 套件 | 标准 | 结果 |
|------|------|------|
| `self_test`（Catch2 v3） | C++14 | **1361 assertions / 604 test cases 全过** |
| `self_test`（含协程 `test_co_mock.cpp`） | C++20 | **1394 assertions / 615 test cases 全过** |
| `thread_terror` | C++14 | exit 0 |
| `custom_recursive_mutex` | C++14 | exit 0（`Pass!`） |
| `compilation_errors`（expect-to-fail） | C++14 | **50/50 PASS / 0 FAIL**（18 个按上游规则排除） |
| `compilation_errors`（expect-to-fail） | C++20 | **68/68 PASS / 0 FAIL**（协程用例全部命中诊断正则） |
| 消费者测试（`test_package`） | C++14 | **5 assertions / 4 test cases 全过** |

- 上游测试用例通过率: **C++14 604/604 + 50/50；C++20 615/615 + 68/68 = 100%**
- 新增测试用例通过率: **4/4（100%）**
- 本地门禁: `conan-verify` G0–G4/L2/L4/L5 **全 PASS**；本地 CI 门禁（与平台同脚本）**L0/L1/L1e/L4 PASS + KC1–KC5/JC1–JC6 全过**（L5 因 header-only 无 bin/lib 产物为 warn）；**W4 独立审计 verdict=pass（P0=0 / P1=0）**
- 关键证据: `archives/t/trompeloeil/49/reports/test-report.md`、`reports/audit-result.json`、`reports/conan-create.log`

## 补充说明

### 路径 B 知识贡献说明

本 PR 按路径 A+B 原子交付：归档适配 + **1 条类级知识草稿**（`knowledge/drafts/`，kv+md 成对，字段经仓内解析器校验齐全）；**关联 Issue：#3048**（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3048）。

**草稿：`DRAFT-11301-ohos-compile-fail-suite` — compile-fail（expect-to-fail）上游测试套件在 OHOS 的执行模型、TMPDIR 固定与诊断锚定治理**

- **一类问题**: 上游把编译期契约编码为"必须编译失败 + 诊断文本匹配"的用例集合，其驱动假设 GNU 用户态（`parallel` 并发、`mktemp` 落 /tmp），其断言依赖特定编译器族的诊断文本。OHOS 用户空间两者都不成立，而"跳过套件"与"套件全过"在流水线上都表现为绿色——该条给出执行模型（等价驱动 + TMPDIR 固定）、逐用例 PASS/FAIL/排除项记账与"不许改写诊断正则"的治理规则。
- **触发实例**: 本 PR 直接触发——`check_errors.sh` 在 OHOS 无法运行（无 `parallel`）；`mktemp` 需 `TMPDIR` 指向构建目录。
- **可复现命令与结果**: `CXX=<clang++> CXXFLAGS="-std=c++14" sh -c 'ls compilation_errors/*.cpp | xargs -P2 -n1 sh ../verify_compilation_error.sh'` → 50 PASS / 0 FAIL（18 个上游规则排除）；`-std=c++20` → 68 PASS / 0 FAIL。配方内以线程池实现同等语义，任一 FAIL 即构建失败。
- **查重差异**: 与 E002（仅 /tmp→TMPDIR）、E063（构建期 -Werror 类别）、E325（test_package 的 shell 解析）不同——本条是**套件执行模型 + 诊断锚定**；与 E418/E423（均为**运行期**负向：PowerShell 绑定 / 破坏性移除包产物）不同——本条断言发生在**编译期**；与 `DRAFT-eigen-3.4.1-test-package-negative-include-boundary`（消费者 include 边界）不同——本条是**上游自带**套件；与 gtest/catch2/cmocka/doctest 系列草稿（测试框架**接线**：CMake components / API 迁移 / CTest 注入 / 子模块转包）不同——本条是"用例断言 = 编译失败"的**执行与诊断**问题。
- **draft-review 实测**: **create（疑似新知）**——类级重写后 TOP1 相似度仅 0.17（E215，LuaRocks Busted harness，主题不同），E423 0.10、E345 0.10；相较重写前的灰区（review-similar → E325 0.40）已无高相似条目。
- **反凑合取舍**: 本次适配另发现"上游 CMake `file(DOWNLOAD)` 兜底静默下载主版本不符的测试框架"问题（实测下载 v2 `catch.hpp` 且编译定义 `-DCATCH2_VERSION=2`）。经查重，该类已由正式条目 **E342** 与 `DRAFT-cmake-test-framework-fetch-to-conan-find-package`（FetchContent 变体）覆盖，故**不单独提交草稿**，仅保留在 `notes.md` 适配记录中——B 贡献只保留真正未被现有知识库覆盖的类级问题。

### 环境与验证方式

- 设备真机: HarmonyOS PC aarch64（clang/clang++ 15.0.4、cmake 4.4.3、Conan 2.29.1 OHOS 适配版）
- 依赖闭包: 仅 `catch2/3.8.1`（tool_requires，制品仓预编译二进制；同时用于消费者测试）
- 门禁链: `conan-verify` G0–G4 → 本地 CI 模拟（W3，`.ci-result.json` exit 0）→ W4 独立审计 pass → submit 前置硬闸

### 关键适配点

1. **禁止构建期联网**: 预置 Catch2 v3 并传给 `CMAKE_PREFIX_PATH`，使上游 `file(DOWNLOAD)` 兜底不可达（详见 `notes.md`；该问题属既有知识覆盖范围，不作为独立草稿提交）。
2. **负向测试驱动替换**: 线程池（2 并发）逐用例执行上游未修改的 `verify_compilation_error.sh`；`TMPDIR` 固定到构建目录（详见 `DRAFT-11301-ohos-compile-fail-suite` 草稿）。
3. **双标准矩阵**: `build()` 内执行 C++14 与 C++20 两轮上游自测 + 两轮负向套件，`conan create` 即完整上游测试门禁（R51）。
4. **编译器来源**: 取 `tools.build:compiler_executables`（R33），不依赖裸 shell 变量。

### 已知限制与未执行项

- header-only 包无 `.a/.so` 产物，因此 L2/L5 类产物检查为 skip/warn；无 debug tarball（无调试符号可打包）。`finalize-archive` 对 `-debug.tar.gz` 的提示属预期。
- `build()` 全量执行上游测试（两个标准 + 68×2 负向编译）约 10 分钟，CI 默认 3600s 预算内实测通过。
- C++14 下 18 个负向用例由**上游自身** `// exception:` 规则排除（协程等），属上游矩阵行为，非本 PR 跳过。

### PR 边界

- 关联 Issue: **#3048**（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3048）；`Closes #3048`
- 源分支: `feat/trompeloeil-49` → 目标分支: `OpenHarmonyPCDeveloper/build_in_harmonyos:main`
- 代码路径: `archives/t/trompeloeil/`（软件级 `README.md`/`manifest.yaml` + `49/`）；相关知识草稿: `knowledge/drafts/DRAFT-11301-ohos-compile-fail-suite.{kv,md}`
- 适配边界: 本 PR 仅包含 trompeloeil 归档与其直接相关知识草稿，未修改框架文件（`ci/`/`scripts/`/`templates/`/`SKILL.md` 等）或其他库；不包含设备 IP、私钥、签名材料、生成的 `ci-metadata.json` 或远端工作区绝对路径。
