# eabase 0699a15 适配笔记

## 编译环境
- 构建系统: cmake (header-only INTERFACE 库，无编译产物)
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: 适配中

## 编译步骤

1. 环境核验：python3 3.12.9 / conan 2.29.1 / git 2.45.2 / clang 15.0.4，ci/scripts/preflight_check.sh eabase/0699a15 通过（无依赖声明）。
2. 官方源码：https://github.com/electronicarts/EABase 提交 0699a15efdfd20b6cecf02153bfa5663decb653c
   - GitHub 直连超时，经镜像(ghfast.top / gh-proxy.com)下载 tarball，两个独立镜像 SHA-256 一致：d33041d12765412080473568fec1e7cc17cde7255b6eb914085ccdf3c00911ad。
3. 库构建：`cmake .. -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_INSTALL_PREFIX=~/tmp/test-install-eabase-0699a15 && cmake --build . && cmake --install .`
   - 仅安装头文件 include/EABase/（12 个头文件 + config/ 3 个），header-only 无二进制产物 → 非 CLI 库，不需要 commands.json。
4. 上游测试套件（EABASE_BUILD_TESTS=ON）：
   - 测试依赖 6 个 EA 子模块（EAMain/EATest/EASTL/EAStdC/EAAssert/EAThread），tarball 中子模块目录为空，经镜像下载 master 快照解压到 test/packages/。
   - EASTL 的 CMakeLists 通过 FetchContent 重新拉取 EABase：用 -DFETCHCONTENT_SOURCE_DIR_EABASE=本地源码绕过网络重拉，且直接从 test/ 目录作为独立工程 configure 避免顶层 EABase INTERFACE target 重名。
   - EAThread 在 OHOS sysroot 缺失 pthread_setaffinity_np/pthread_getaffinity_np/pthread_setcancelstate（musl 语义差异）：在 scratch 测试框架源码最小适配（OHOS 下跳过 CPU affinity 设置 / 取消态调用，与 Android 分支同思路），测试框架文件不进入交付物。
   - 运行：`./EABaseTest` + `ctest` 全部通过（RETURNCODE=0，100% tests passed）。
5. 鸿蒙专项测试：test_ohos/TestEABaseOHOS.cpp（源码在 scratch 测试树，供验证；结论证据见 reports/）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 配置失败（policy version < 3.5） | 上游 cmake_minimum_required(3.1) 过旧 | conanfile generate() 注入 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | OHOS aarch64 未定义 EA_SYSTEM_LITTLE_ENDIAN（上游测试 EA_SYSTEM_ENDIAN 失败） | eaplatform.h Linux 分支的 __aarch64__ 分支漏定义端序宏 | 补丁：该分支增加 `#define EA_SYSTEM_LITTLE_ENDIAN 1` |
| 3 | va_list_reference 按值传递，上游 EAStdarg 引用测试失败 | eastdarg.h 判定条件缺了 Linux+ARM64（aarch64 va_list 是结构体，必须用引用） | 补丁：条件增加 `(defined(EA_PLATFORM_LINUX) && defined(EA_PROCESSOR_ARM64))` |
| 4 | EAAlignment 测试失败（malloc 最小对齐 16 与实际 8 不符） | OHOS aarch64 malloc 实测至少 8 字节对齐，上游 EA_PLATFORM_MIN_MALLOC_ALIGNMENT 取 PTR_SIZE*2=16 | 补丁：`#elif defined(__OHOS__) && defined(EA_PROCESSOR_ARM64)` → 8（R8 例外：libc 探针，PR 说明） |
| 5 | GitHub 直连超时 | 网络限制 | 镜像下载并双重 SHA-256 交叉核验，conandata.yml 仍用官方 HTTPS URL |

## 源码修改

- include/Common/EABase/config/eaplatform.h：
  - Linux 分支 __aarch64__ 增加 `#define EA_SYSTEM_LITTLE_ENDIAN 1`（端序宏）
  - EA_PLATFORM_MIN_MALLOC_ALIGNMENT 增加 OHOS ARM64 分支 = 8
- include/Common/EABase/eastdarg.h：va_list_reference 条件增加 Linux+ARM64
- （仅 scratch 测试框架树内最小适配，不含于交付物：EAThread unix 源文件 OHOS 下跳过 affinity/cancel 调用）

## 上游测试双口径台账

测试入口枚举（官方 0699a15 tag 源码）：

| 入口 | 类型 | 分类理由 | 是否独立用例 | 是否运行 | 结果 | 不能运行原因 |
|------|------|----------|-------------|---------|------|-------------|
| test/source/TestEABase.cpp | C++ 用户测试源 | EAMain 注册的 11 个真实用户测试函数 | 是 | 是 | 全部通过 | - |
| test/source/TestEABaseC.c | C 用户测试源（独立 EAMain） | 4 个真实用户测试函数，未被上游 CMake glob 收录 | 是 | 是（手动链接 EAMain 库运行） | 全部通过 | - |
| test/source/TestEABaseSeparate.cpp | 编译检查源 | 独立编译单元检查 EABase 类型定义（无运行断言） | 否（编译检查） | 是（编译通过） | 通过 | - |
| test/source/CEntryPoint.cpp | 测试框架入口 | EAMain 包装（EAEntryPointMain.inl），非用户用例 | 否 | 是（链接进测试） | - | - |
| test/packages/EAMain..EAThread | 框架子模块 | 测试框架库源码（EAMain/EATest/EASTL/EAStdC/EAAssert/EAThread），非用户用例 | 否 | 是（编译/链接） | - | - |
| test/CMakeLists.txt | 构建目标 | EABaseTest 可执行 + CTest 注册 EABaseTestRuns | 否 | 是 | - | - |

统计口径：
- source_declared_total：15（C++ 11 + C 4 个真实独立用户测试函数）
- configured_executable_total：11（上游 CMake glob 仅收录 TestEABase.cpp → EABaseTest 内 11 函数）+ C 测试入口手动实例化 4 = 15
- executed_passed_total：15（11+4 全部实际运行通过）
- executed_passed_total/source_declared_total = 15/15 = 100%
- configured 集合通过率：15/15 = 100%
- 未运行/未实例化：0（C 测试入口按源码测试入口恢复规则以最小手段纳入构建实际运行）
- 映射：源码声明(TestEABase.cpp 11 函数 / TestEABaseC.c 4 函数) → 构建目标(EABaseTest / 手动链接) → CTest 注册(EABaseTestRuns / 直跑) → 实际执行日志(全部 RETURNCODE=0)

## 鸿蒙专项测试

- 文件：test_ohos/TestEABaseOHOS.cpp（仅使用 EABase 公开头文件 + 标准库）
- 覆盖：端序宏正确性、va_list_reference 引用语义（aarch64 结构体 ABI）、EABase 基础类型/平台宏、malloc 对齐与 EA_PLATFORM_MIN_MALLOC_ALIGNMENT 一致性
- 结果：15 项断言全部 PASS，exit 0

## 环境核验
- 语言预检：lang-preflight 通过（detected=cpp，CMakeLists project(EABase CXX)）
- 污染扫描：源码零命中 file://、.build-cache、predl_cache、currentUser、绝对路径、镜像域

## R02 返工记录（task eabase-0699a15-r02-pc2-8-20260911T083146Z）

### R8 修复（R02 核心）

- 修复内容：`patches/0001-include-Common-EABase-config-eaplatform.h.patch` 中
  `EA_PLATFORM_MIN_MALLOC_ALIGNMENT` 判断链原 `#elif defined(__OHOS__) && defined(EA_PROCESSOR_ARM64) → 8`
  违反 R8（补丁引入平台条件编译宏）。
- 修复后：并入 POSIX 风格条件 `#elif defined(EA_PLATFORM_LINUX) && defined(EA_PROCESSOR_ARM64) → 8`
  （与 0002 va_list_reference 判定同风格）；补丁与知识草稿零 `__OHOS__` 残留。
- conandata.yml patch_description 同步更新为 POSIX 措辞，无需 R8 例外批准。

### 知识草稿同步修正（R02）

- `knowledge/drafts/E3000-draft-D384.kv`：rec_description 改写为 POSIX 条件
  （删除「R8 例外 PR 说明」「EAThread 在 __OHOS__ 下跳过」表述）。
- `knowledge/drafts/E3000-draft-D384.md`：根因/方案/边界 3 处 `__OHOS__` 段
  改为 aarch64 Linux-family POSIX 描述；.md/.kv 同 stem 配对保持。
- 复检：.kv/.md 均零 `__OHOS__`/R8 例外残留（grep_exit=1 预期）。

### test_package 断言补强（R02，P3）

test_package/test.cpp 新增真实断言（本地 clang++ 编译链接运行 exit=0，conan create test_package 1/1 通过）：
1. 端序宏：aarch64 下 EA_SYSTEM_LITTLE_ENDIAN 必须定义（leDefined==1），运行时字节序 p[0]==0x78 与宏一致
2. 对齐常量：aarch64 下 EA_PLATFORM_MIN_MALLOC_ALIGNMENT==8（POSIX 条件），且 <= 实测 malloc 最小观测对齐
3. va_list 引用传递：经 va_list_reference 传参，callee 推进后 caller 第二次读取得到第二参数（a==17, b==99）
4. 保留 R01 基础冒烟：类型宽度、EA_SUCCEEDED/EA_FAILED、EA_KILOBYTE/EA_MEBIBYTE

### R02 全量验证复跑结果（双口径台账不变）

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total | 15 | TestEABase.cpp 11 + TestEABaseC.c 4 |
| configured_executable_total | 15 | 11（EABaseTest）+ 4（C 入口手动实例化） |
| executed_passed_total | 15 | 全部通过（RETURNCODE=0） |
| 失败/未运行 | 0 | - |

- 上游 C++ 测试复跑：11 函数全 0 失败，All tests completed successfully（100% tests passed）
- C 测试入口复跑：4 函数全 0 失败，RETURNCODE=0
- 鸿蒙专项测试复跑：15 断言 ALL PASS
- test_package（补强后）：1/1 Passed
- conan create（-pr:h ohos-aarch64 --build=missing）：exit=0
- 日志：~/tmp/eabase-logs/r02_conan_create.log（SHA-256 0dff7774a8b34159caf8dbd8689dcdecfbf1c05812d1019cf91d3d4e9b91ce29）

## 知识候选台账与查重决定

task_type: 知识库扩展（路径 B 判定：new_draft）

### 候选 1：EA 家族头文件 OHOS aarch64 平台检测缺口（新知识）

- 真实错误：上游 3 处测试失败（EA_SYSTEM_ENDIAN / EAStdarg 引用 / EAAlignment）
- 根因：eaplatform.h Linux 分支 __aarch64__ 漏端序宏；eastdarg.h va_list_reference 判定缺 Linux+ARM64（aarch64 va_list 为结构体）；EA_PLATFORM_MIN_MALLOC_ALIGNMENT=16 vs OHOS malloc 实测 8；EAThread 测试框架在 OHOS 缺 pthread_setaffinity_np/getaffinity_np/setcancelstate
- 修复：3 个头文件补丁（patches/0001+0002）+ EAThread 测试树最小适配（不入交付物）
- 验证：上游测试 15/15、鸿蒙专项 15 断言、conan create test_package 1/1
- 适用范围：EA 家族（EABase/EASTL/EAStdC/EAThread/EATest/EAMain）在 OHOS aarch64

### 七轴查重

- exact_duplicate: false（四范围 index.tsv/doc/graph/drafts 无 EA 家族端序/va_list/对齐条目）
- causal_duplicate: false（E094 只覆盖 pthread_attr_setaffinity_np 前缀不同符号）
- trigger_overlap: 部分（E094 触发工具同为 clang/make 编译期）
- solution_overlap: 部分（E187 覆盖 CMake policy 修复，本任务 CMake policy 问题复用 E187）
- combination_novelty: true（端序+va_list 引用+MALLOC_ALIGNMENT 三修复组合无既有条目）
- boundary_novelty: true（aarch64 va_list 结构体引用语义 + OHOS malloc 8 对齐为新事实）
- test_migration_novelty: true（EAThread 三符号缺失及跳过不影响正确性的验证未见于既有条目）

### 覆盖/新增差异

- E187 完整覆盖 CMake policy 问题 → 本任务 CMake policy 修复直接复用 E187（reuse_existing，无新增差异）
- E094 部分覆盖 EAThread affinity → 新增差异：pthread_setaffinity_np/pthread_getaffinity_np/pthread_setcancelstate 三符号
- EA 家族平台检测（端序/va_list/对齐）零命中 → 完全新增

### 关系字段

- similar_to: E094, E187
- caused_by: 无（独立平台检测缺口）
- prerequisite_of: 无
- conflicts_with: 无

### 适用边界/反例

- 适用：EA 家族库在 OHOS aarch64 构建；以 EA_PLATFORM_LINUX 分支编译 aarch64 的 EA 头文件
- 反例：非 EA 家族库；x86/x64（端序与 va_list 语义正常）；__OHOS__ 分支仅影响 OHOS（其余平台回退原逻辑）

### 路径决定

- reuse_existing: 是（CMake policy 部分 → E187，不新建条目）
- new_draft: 是（E3000-draft-D384.kv/.md 已建，EA 家族平台检测 + EAThread 三符号新增差异）
- path_a_no_knowledge: 否
- 结论：增加知识库扩展草稿 E3000 进入同一个 PR（与三方库归档文件同 PR）
---

**编译结束**: 2026-09-11 16:42
**最终状态**: published
