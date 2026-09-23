# fmt 9.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-20
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 源码核验（bootstrap_audit）
- 官方 URL: https://github.com/fmtlib/fmt/archive/refs/tags/9.1.0.tar.gz（官方 tag，GitHub release 2022-08-27）
- 版本确认: ChangeLog.rst "9.1.0 - 2022-08-27"；include/fmt/core.h FMT_VERSION=90100
- SHA-256: 5dea48d1fcddc3ec571ce2058e13910a0d4a6bab4cc09a809d8b1dd1c88ae6f2
  （官方 codeload.github.com 直下载 tarball 与本地缓存 sha256 完全一致，双重来源交叉核验）
- 构建系统: CMake（顶层 CMakeLists.txt，FMT_TEST 选项控制测试目标）
- 依赖: 无外部第三方依赖（requirements 为空）
- 已有归档参考: archives/f/fmt/8.1.1（首个鸿蒙配方）、11.1.3、12.2.0 可复用配方经验
- 污染扫描: 归档目录无 file://、.build-cache、predl_cache、currentUser 绝对路径残留

## 上游测试完整枚举台账

### 一、用户测试源（test/*.cc，独立 TEST()/TEST_F() 用例计数）

| 文件 | TEST() | TEST_F() | 是否独立用例 | 分类理由 |
|------|--------|----------|-------------|----------|
| args-test.cc | 12 | 0 | ✅ | 用户参数格式化用例 |
| assert-test.cc | 2 | 0 | ✅ | 用户断言用例 |
| chrono-test.cc | 27 | 0 | ✅ | 用户 chrono 格式化用例 |
| color-test.cc | 3 | 0 | ✅ | 用户颜色用例 |
| compile-fp-test.cc | 1 | 0 | ✅ | 用户编译期浮点用例 |
| compile-test.cc | 30 | 0 | ✅ | 用户编译期格式化用例 |
| core-test.cc | 47 | 0 | ✅ | 用户核心 API 用例 |
| enforce-checks-test.cc | 0 | 0 | ⚠️ 非独立 | 仅 API 编译练习（FMT_ENFORCE_COMPILE_STRING），无 TEST 注册 |
| format-impl-test.cc | 30 | 0 | ✅ | 用户实现细节用例 |
| format-test.cc | 113 | 0 | ✅ | 用户核心格式化用例（最大） |
| gtest-extra-test.cc | 17 | 6 | ✅ | 用户测试（测试 fmt 的 gtest 扩展辅助） |
| header-only-test.cc | 1 | 0 | ✅ | 用户头文件模式用例（并入 format-impl-test 目标） |
| module-test.cc | 47 | 0 | ⚠️ 未实例化 | 用户用例但仅 FMT_CAN_MODULE（需 MSVC+C++20 模块）时构建；clang 15/OHOS 下 FMT_CAN_MODULE=OFF，不实例化 |
| noexception-test.cc | 0 | 0 | ⚠️ 非独立 | 编译练习（-fno-exceptions，FMT_PEDANTIC 才构建），无 TEST |
| os-test.cc | 53 | 0 | ✅ | 用户 OS 相关用例 |
| ostream-test.cc | 21 | 0 | ✅ | 用户 ostream 集成用例 |
| posix-mock-test.cc | 20 | 0 | ✅ | 用户 POSIX mock 用例 |
| printf-test.cc | 38 | 0 | ✅ | 用户 printf 兼容用例 |
| ranges-odr-test.cc | 1 | 0 | ✅ | 用户 ODR 用例（并入 ranges-test 目标） |
| ranges-test.cc | 26 | 0 | ✅ | 用户 ranges 格式化用例 |
| scan-test.cc | 10 | 0 | ✅ | 用户 scan 用例 |
| std-test.cc | 4 | 0 | ✅ | 用户 std 集成用例 |
| unicode-test.cc | 2 | 0 | ✅ | 用户 unicode 用例 |
| xchar-test.cc | 32 | 0 | ✅ | 用户宽字符用例 |

**用户测试源合计：TEST()=537 + TEST_F()=6 = 543 个独立上游用例（source_declared_total=543）**

### 二、框架/支撑文件（不计独立用例）

| 路径 | 类型 | 说明 |
|------|------|------|
| test/gtest/ | gtest 框架 | 内置 gtest（gmock-gtest-all.cc 等 4 文件），框架内部，非用户用例 |
| test/gtest-extra.cc/h | 框架扩展 | fmt 自定义 gtest 扩展辅助（被测对象是 gtest-extra-test.cc 的用户用例） |
| test/test-main.cc | 测试入口 | gtest main |
| test/util.cc/h | 工具 | 测试公共工具函数 |
| test/mock-allocator.h | fixture | mock 分配器 fixture |
| test/scan.h | 工具 | scan 测试工具头 |
| test/test-assert.h | 工具 | 断言辅助头 |
| test/detect-stdfs.cc | 探测脚本 | CMake try_compile 探测（0 用例） |
| test/compile-error-test/ | 编译错误验证 | ctest --build-and-test（FMT_PEDANTIC 才注册），非用户 TEST 用例 |
| test/find-package-test/ | 集成测试 | ctest --build-and-test（FMT_PEDANTIC），非独立 TEST 用例 |
| test/add-subdirectory-test/ | 集成测试 | ctest --build-and-test（FMT_PEDANTIC），非独立 TEST 用例 |
| test/static-export-test/ | 集成测试 | ctest --build-and-test（FMT_PEDANTIC），非独立 TEST 用例 |
| test/cuda-test/ | CUDA 测试 | FMT_CUDA_TEST=OFF，OHOS 无 CUDA，不实例化 |
| test/fuzzing/ | fuzz harness | 8 个 libFuzzer 入口（chrono-duration/chrono-timepoint/float/named-arg/one-arg/two-args/main/fuzzer-common.h），FMT_FUZZ=OFF，非单元测试用例 |

### 三、CMake 注册的测试目标（test/CMakeLists.txt，add_fmt_test/add_test）

默认配置（FMT_TEST=ON, FMT_PEDANTIC=OFF, FMT_MODULE=OFF, FMT_CUDA_TEST=OFF）实例化 20 个可执行测试目标：
args-test / assert-test / chrono-test / color-test / core-test / gtest-extra-test / format-test /
format-impl-test(+header-only-test.cc) / ostream-test / compile-test / compile-fp-test / printf-test /
ranges-test(+ranges-odr-test.cc) / scan-test / std-test / unicode-test / xchar-test / enforce-checks-test(0用例) /
posix-mock-test / os-test

**configured_executable_total = 496 个用例**（543 源声明 − 47 module-test 未实例化；其余 543−496=47 全部为 module-test 一个目标）
- 未实例化原因：module-test 仅 FMT_CAN_MODULE 时构建，而 FMT_CAN_MODULE 门控要求 C++20+MSVC 模块支持，
  clang 15/OHOS 工具链不支持，FMT_MODULE=OFF（CMakeLists.txt L86-92 明确 set(FMT_CAN_MODULE OFF)）
- 其余 6 个 TEST 用例（gtest-extra-test TEST_F）已在 configured 目标内

### 四、统计口径
- source_declared_total（官方 tag 源码按可复制枚举规则）: **543**
- configured_executable_total（当前 OHOS 配置实例化）: **496**
- executed_passed_total / 未运行数: 以实际构建运行为准（见验证结果）
- 样例（doc/）、基准（benchmarks/，9.1.0 无独立 benchmarks 目录）、support/ 构建支撑均非测试用例

## 编译步骤

1. `ohc-run.py init-build fmt 9.1.0 --url=https://github.com/fmtlib/fmt/archive/refs/tags/9.1.0.tar.gz`
   （tarball 预置 ~/tmp/builds/，SHA-256 交叉核验一致）
2. `ohc-run.py conan-init fmt 9.1.0` → 生成 conanfile.py/conandata.yml/test_package
3. 按 8.1.1/12.2.0 已验证配方改写 conanfile.py 为 cmake 模板（OHOS cmake_system_name 守卫、
   FMT_TEST=OFF/FMT_DOC=OFF/FMT_INSTALL=ON、_sign_binaries、includedirs 只声明 include 层）
4. 编写 9.1.0 专用 test_package（test.cpp 9 项断言）与 conandata.yml（官方 SHA-256）
5. `ohc-run.py conan-verify fmt 9.1.0` → G0/G1/G2/G3/G4/L2/L4/L5 全 PASS
   （G2 conan create 含 test_package 运行：`fmt OK: 9 CHECK passed, FMT_VERSION=90100`）
6. 上游测试实跑：OHOS toolchain（CC=/data/service/hnp/bin/clang）cmake -DFMT_TEST=ON 构建 68 目标、
   20 个 ctest 可执行目标，`ctest --output-on-failure` 20/20 全 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 把归档脚手架写到 skill 根而非 worktree | find_project_dir() 优先命中 skill 根 SKILL.md | 设 OHC_PROJECT_DIR=<worktree> 重新脚手架 |
| 2 | G1 校验缺 export_sources() 方法 | 模板未含该方法 | 配方补 export_sources()（export_conandata_patches），对齐 11.1.3 |
| 3 | G2 test_package 编译失败：std::__thread_id 无 formatter | test.cpp 漏包含 fmt/std.h | 补 `#include <fmt/std.h>` 后重跑 G2 通过 |

## 依赖版本

- CMake: 4.1.2 / Ninja + Unix Makefiles
- Clang: 15.0.4（OHOS NDK，target aarch64-unknown-linux-ohos，/data/service/hnp/bin）
- Conan: 2.29.1（OHOS 适配版），profile ohos-aarch64
- 无外部运行时依赖（vendored gtest 仅供上游测试）

## 验证结果

```bash
# conan-verify（含 conan create + test_package）
ohc-run.py conan-verify fmt 9.1.0 → G0-G4/L2/L4/L5 全 PASS
test_probe 输出: fmt OK: 9 CHECK passed, FMT_VERSION=90100

# 上游测试（OHOS toolchain 实测）
cmake -DCMAKE_SYSTEM_NAME=OHOS -DFMT_TEST=ON ... && cmake --build . -j4  # 68/68 目标
ctest --output-on-failure -j2  →  20/20 passed, 0 failed

# 双口径台账
source_declared_total   = 543（24 个用户测试源，537 TEST + 6 TEST_F）
configured_executable_total = 496（20 个 ctest 目标注册的全部用例）
executed_passed_total   = 496（全部配置目标实跑通过）
uninstantiated          = 47（module-test：仅 FMT_CAN_MODULE（需 MSVC+C++20 模块）时构建，
                               clang 15/OHOS 下 FMT_CAN_MODULE=OFF，源码声明但未实例化）
全量通过率 = 496/543 (91.3%)；当前配置可执行集合通过率 = 496/496 (100%)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | cmake 配方（OHOS 守卫+签名+include 层策略） |
| conandata.yml | 官方 URL + SHA-256 5dea48d1… |
| test_package/ | 消费者验证（test.cpp 9 断言，conan create 时实跑通过） |
| notes.md | 本笔记（含完整枚举台账） |

## 注意事项

- fmt/std.h 在 9.1.0 支持 std::thread::id/filesystem::path/monostate/variant，尚不支持 std::optional（12.x 才有）
- 八进制前缀 9.1.0 仍为 "0"（"010"），"0o" 是后版本行为；断言须钉在本版本
- includedirs 只声明 include 层（不展开 include/fmt），避免 fmt/locale.h 遮蔽 musl locale.h（spdlog 实撞史）

## 知识候选台账 + 查重（路径 B 判定）

### 候选 1：fmt/std.h 版本能力矩阵（std::optional 12.x 才有）+ 八进制前缀版本钉定
- 真实错误：G2 test_package 首错 `fmt/core.h:1756 static assertion failed due to requirement 'formattable': Cannot format an argument`（std::__thread_id 无 formatter，漏 include fmt/std.h）
- 根因：fmt/std.h 各版本支持 std 类型集合不同——9.1.0 有 thread::id/filesystem::path/monostate/variant，std::optional 是 12.x 新增；八进制前缀 8.x~9.x 为 "0"（"010"），"0o" 是后版本行为（8.1.1 notes 推测"0o 是 fmt 9+ 才改"被 9.1.0 实测证伪）
- 修复：显式 #include <fmt/std.h>；断言按目标版本钉定
- 验证：G2 conan create 通过（`fmt OK: 9 CHECK passed, FMT_VERSION=90100`）；上游 ctest 20/20 全过（format-test 断言行 `{0:#o}` 042 → "042" 通过）
- 适用范围：任何消费 fmt 的库/配方的 test_package 与下游断言（spdlog、mitama-cpp-result 等）
- 四范围查重：正式知识 index.tsv 未命中（无 fmt/std.h 能力条目）；图谱 .kv 未命中；草稿库无同内容（libcxx15-format-stub 讲 std::format 标准库 stub，与 fmt 自身无关）；doc/ 未覆盖
- 七轴查重结果：exact/causal=否；trigger_overlap=部分（formatter 关键词与 libcxx stub 类重叠）；solution_overlap=部分（都涉及 include/探测）；combination_novelty/boundary_novelty/test_migration_novelty=是
- 决定：**new_draft**（同 stem .kv/.md 已建，见 knowledge/drafts/DRAFT-fmt-9.1.0-std-h-version-capability-matrix.{kv,md}）

### 候选 2：conan-init 生成的配方缺 export_sources() 导致 G1 校验 FAIL
- 真实错误：conan-verify G1 FAIL "conanfile.py 缺少 export_sources() 方法"
- 根因：autotools 模板未含该方法（框架模板缺陷，非本库缺陷）
- 修复：配方补 `def export_sources(): export_conandata_patches(self)`（对齐 11.1.3 先例）
- 判定：既有先例方案（11.1.3 conanfile）已覆盖，属常见配方错误修复，不入知识库（知识库已有解决方案，下一轮沿用即可）

### 候选 3：init-build 脚手架落 skill 根而非 worktree
- 真实错误：init-build 把归档脚手架写到 ~/.opendesk/.../archives 而非 worktree
- 根因：ohc-run.py find_project_dir() 优先命中 skill 根 SKILL.md（工具行为）
- 修复：设 OHC_PROJECT_DIR=<worktree> 重新脚手架（已知恢复规则类，非可跨库知识）
- 判定：噪声/工具使用问题，不入知识库

### 候选 4：OHOS cmake_system_name 守卫 + 签名 + includedirs 只声明 include 层
- 已由 8.1.1/11.1.3/12.2.0 配方及既有知识覆盖，本轮按先例复用，无新增差异，不入库

**路径决定：new_draft（路径 B），PR 前缀【知识库扩展】；候选 2-4 无新增知识价值，不建草稿。**
---

**编译结束**: 2026-09-21 00:13
**最终状态**: built
