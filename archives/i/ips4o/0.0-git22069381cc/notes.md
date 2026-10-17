# ips4o 0.0-git22069381cc 适配笔记

## 编译环境
- 构建系统: 无（header-only 头文件库，commit 22069381cc 无 CMake/Makefile/configure）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4（OHOS aarch64 profile: os=OHOS arch=armv8 cppstd=17）
- 状态: built（conan-verify G1-G4 全 PASS，CI 上传待 PR 合并 main 后由 release 流水线执行）

## 编译步骤

1. `ohc-run.py init-build ips4o 0.0-git22069381cc --url https://github.com/vgteam/ips4o/archive/22069381cc1bf2df07ee1ff47f6b6073fcfb4508.tar.gz`
   - tarball SHA-256: `3a228962bab8d37566cef2f8eae99a15db739cdf79b0de1bceea6c3559f2f1b4`（下载后 sha256sum 复核一致）
   - 依赖解析: 0 依赖（`requirements()` 为空）
2. `ohc-run.py lang-preflight ips4o 0.0-git22069381cc --src <work>` → exit 0，detected=cpp，主体占比 100%
3. 无 configure/make（header-only，无构建系统）。本地编译冒烟验证：
   - `clang++ -std=c++14 -O2 -fopenmp -pthread -I <work> smoke.cpp -o smoke_omp`（exit 0，运行输出 `SMOKE_OK sequential+parallel sorted verified`，RUN_EXIT 0）
   - 仅顺序排序：`clang++ -std=c++14 -O2 -I <work> seq_only.cpp -o seq_only`（exit 0，运行 `SEQ_ONLY_OK`，RUN_EXIT 0）—— 顺序 `ips4o::sort` 不依赖 OpenMP/线程即可编译链接
   - 并行 `ips4o::parallel::sort` 需要 OpenMP 运行时（`#include <omp.h>` 无条件包含于 thread_pool.hpp），属消费者编译期选择（`-fopenmp` 或链接 libomp）
4. `ohc-run.py conan-init ips4o 0.0-git22069381cc`（autotools 模板误判，已重写为 header-only 配方）
5. 手写修正：conanfile.py 重写为 header-only（package_type=header-library，无编译阶段，只安装头文件）；conandata.yml 补 sha256；test_package 由 C 空壳 print 测试重写为 C++ 真实调用 `ips4o::sort` 并对比 `std::sort`（R34）
6. `ohc-run.py conan-verify ips4o 0.0-git22069381cc --profile ohos-aarch64` → exit 0，G1 配方完整性 PASS / G2 conan create PASS / G3 系统同名库隔离 PASS / G4 产物完整性 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 按 autotools 生成配方（configure+make） | 构建系统检测对无构建系统库误判为 autotools | 按 v12.21 header-only 模板重写 conanfile.py：无 build()，package() 仅 copy 头文件与 LICENSE |
| 2 | conandata.yml sha256 为 REPLACE 占位符 | 模板未回填 | 填入实测 `3a228962bab8d37566cef2f8eae99a15db739cdf79b0de1bceea6c3559f2f1b4` |
| 3 | test_package 为 C print 空壳测试 | autotools 模板生成，违反 R34 | 重写为 C++ test.cpp：include `<ips4o.hpp>`，调用 `ips4o::sort` 与 `std::sort` 比对结果，可观察断言 |
| 4 | G1 要求 build()/export_sources()/补丁应用方法 | G1 结构检查硬性要求方法存在 | 补 `build()`（仅 apply_conandata_patches，空补丁 no-op）+ `export_sources()`，不伪造编译产物 |
| 5 | 并行排序链接需 OpenMP 符号 | thread_pool.hpp 无条件 `#include <omp.h>` 且使用 omp_* 函数 | 配方不引入依赖；消费者编译并行路径需 `-fopenmp`，顺序路径无要求。记入注意事项 |

## 源码修改

无补丁（patches 为空）。header-only 库未修改任何上游源码。

## 依赖版本

- 依赖: 无（requirements() 为空，conan-verify 确认 0 依赖解析成功）
- 工具链: clang 15.0.4 / cmake 4.1.2 / conan 2.29.1（OHOS 适配版）

## 上游测试枚举台账（R51 / 双口径）

**枚举证据**：官方 tarball（`ips4o-22069381cc1bf2df07ee1ff47f6b6073fcfb4508.tar.gz`）全量 22 个文件，目录结构仅
`ips4o.hpp`（顶层）+ `ips4o/`（19 个头文件）+ `LICENSE` + `README.md`，无任何测试文件/目录。

| 枚举项 | 是否存在 | 分类理由 | 是否独立上游用例 |
|---|---|---|---|
| 测试源文件（test/、tests/、*test*.cpp） | 无（find 无匹配） | 源码树无测试目录 | 否（不存在） |
| 测试框架头/源码（catch2/gtest/doctest 等） | 无 | 无框架引入 | 否（不存在） |
| 样例（example/） | 无 | README 仅含内联用法示例代码，无独立文件 | 否（不存在） |
| 基准（benchmark/） | 无 | 无基准目录 | 否（不存在） |
| fixture/脚本（*.sh/*.py/configure） | 无 | 无任何脚本与构建入口 | 否（不存在） |
| 构建目标（CMakeLists/Makefile/ctest 注册） | 无 | 无构建系统文件 | 否（不存在） |

**双口径统计**：
- `source_declared_total` = **0**（官方 tag 源码中无可复制枚举的测试声明；证据=上述全量文件清单，SHA-256 `3a2289...f1b4`）
- `configured_executable_total` = **0**（无构建系统，无可实例化/注册用例）
- `executed_passed_total` = **0**，失败 = **0**，未运行/未实例化 = **0**
- 全量通过率：0/0（上游无测试，非"未运行"，为"确无测试"——R51 清点证据已附）
- 映射表：声明/注册项 → 无 → 构建目标 → 无 → ctest -N/GTest 注册项 → 无 → 实际执行日志 → 无

**依赖可用性复查**：ips4o 0 依赖，无因依赖未运行的上游测试入口，无需 registry 复查。

## 鸿蒙专项测试（与上游/消费者分别计数）

- test_package/test.cpp：消费者用例（见 test_package/MANIFEST.yml）——include 已安装公开头 `<ips4o.hpp>`，调用 `ips4o::sort`，与 `std::sort` 结果逐元素比对，可观察 PASS/FAIL 输出
- 鸿蒙专项验证：本地编译冒烟 `smoke_omp`（含并行路径）与 `seq_only`（顺序路径）均编译运行通过；`conan create`（OHOS profile）内 test_package 实际编译链接运行通过（G2 PASS）

## 注意事项

- 并行排序 API `ips4o::parallel::sort` 需要 OpenMP：消费者需以 `-fopenmp` 编译（thread_pool.hpp 无条件包含 `<omp.h>`）；顺序 `ips4o::sort` 无额外要求
- 该 commit 无需 `-mcx16`（aarch64 原生 16 字节原子指令）；x86 目标才需要
- 版本号 `0.0-git22069381cc` 采用仓库 git snapshot 惯例（上游无 release tag）

---

## 知识候选台账与查重（knowledge_candidate_ledger）

查重范围：正式知识（knowledge/graph/index.tsv + E*.kv）、图谱文档（knowledge/doc/E*.md）、
草稿（knowledge/drafts/）四范围逐一核验。路径初判：**路径 B（知识库扩展，new_draft）**。

### 候选 C1 — header-only 无构建系统库被 conan-init 误判 autotools / G1 需要显式 build()

- 真实错误: conan-init 按 autotools 生成 configure+make 配方（G1 报 conanfile.py 缺少 build()/export_sources()/补丁应用调用）
- 根因: 构建系统检测对无构建系统 header-only 库误判 autotools；G1 结构门禁要求 build() 方法存在（结构检查非编译检查）
- 修复: 按 header-only 模板重写配方（package_type=header-library，no-op build() 仅 apply_conandata_patches，package() 仅 copy 头文件）；G1 通过
- 验证: conan-verify G1-G4 全 PASS；W3 conan create PASS
- 适用范围: 所有 header-only / 无构建系统 C++ 库
- 查重: **exact_duplicate = true** —— E257（no-op-build-for-header-only，bshoshany-thread-pool 5.0.0 正式条目）错误签名 `G1: FAIL|conanfile.py 缺少: build() 方法` 与本次完全一致，root_cause/rec_approach 同源（E257 覆盖 G1 build() 门禁 + header-only 配方要点）
- 七轴: exact_duplicate ✓ / causal_duplicate ✓（同根因）/ trigger_overlap ✓ / solution_overlap ✓ / combination_novelty ✗ / boundary_novelty ✗（export_sources/补丁方法同属 G1 结构门禁族，E257 影响面已含）/ test_migration_novelty ✗
- 决定: **reuse_existing（复用 E257，不建新草稿）**

### 候选 C2 — OHOS 直接 clang 命令行链接 C++ 消费者缺 libc++/libc++abi 运行时符号

- 真实错误: `ld.lld: error: undefined symbol: std::logic_error::logic_error(char const*)` / `vtable for std::length_error` / `std::bad_array_new_length::bad_array_new_length()`（run_ohos_test.py 直接 clang 链接）
- 根因: OHOS SDK clang 15 驱动默认链接配置不携带 libc++/libc++abi 搜索路径；库实际在 `<SDK>/ohos/native/llvm/lib`，直接 clang 通道（非 CMake toolchain）不自动注入
- 修复: `-stdlib=libc++ -L <SDK llvm/lib> -lc++ -lc++abi`（并行路径再加 `-fopenmp`）
- 验证: 补齐 flags 后 `OHOS_IPS4O_TESTS_PASS parallel=4M comparator=1M` exit 0（test_ohos/run_ohos_test.py）
- 适用范围: 所有直接 clang 命令行通道（鸿蒙专项测试脚本、独立消费者、Makefile 直连 clang）
- 查重: 部分覆盖 —— E191（unable to find library -lc++，CMake 侧）同根因不同表现面；E455（-stdlib=libstdc++ 拒绝）相邻；均未覆盖"直接 clang 通道符号缺失 + 显式 flags 组合"
- 七轴: exact_duplicate ✗ / causal_duplicate 部分（根因同 E191，表现面不同）/ trigger_overlap 部分 / solution_overlap 部分（E191 为 CMake 变量注入，本候选为命令行 flags）/ **combination_novelty ✓**（-stdlib=libc++ + -L SDK lib + -lc++ -lc++abi 组合为新增差异）/ **boundary_novelty ✓**（直接 clang 非 CMake 通道边界）/ test_migration_novelty ✓（run_ohos_test.py 类脚本可跨库复用）
- 关系: similar_to=[E191, E455], caused_by=[], prerequisite_of=[], conflicts_with=[]
- 决定: **new_draft** → `knowledge/drafts/DRAFT-ips4o-0.0-git22069381cc-ohos-direct-clang-link-libcxx.kv/.md`（同 stem 配对）

### 候选 C3 — ips4o 并行排序 API 需要 OpenMP

- 真实错误: 并行路径链接报 omp_get_max_threads/omp_get_num_threads 等未定义符号（无 -fopenmp 时）
- 根因: thread_pool.hpp 无条件 `#include <omp.h>` 并使用 OpenMP 运行时；顺序排序不实例化并行符号
- 修复: 消费者 `-fopenmp`（配方不引入依赖，属编译期选择）
- 查重: E127（pthread_cancel/libomp 编译面）不覆盖消费者编译 flag 要求；标准 C++/OpenMP 行为，无跨库新差异
- 七轴: 全轴 ✗（无新增知识）
- 决定: **path_a_no_knowledge**（记为 notes.md 注意事项，不建草稿）

### 最终路径决定

- 路径 B（知识库扩展）：候选 C2 已验证、可跨库复用、查重部分覆盖且有新增差异 → new_draft
- 草稿: `knowledge/drafts/DRAFT-ips4o-0.0-git22069381cc-ohos-direct-clang-link-libcxx.kv` + `.md`（同 stem 配对）
- 候选 C1 复用 E257；候选 C3 无知识价值
- PR 前缀: 【知识库扩展】（new_draft 且 .md/.kv 配对通过）
---

**编译结束**: 2026-09-28 10:03
**最终状态**: built
