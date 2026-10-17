# arena 20260923 适配笔记

## 编译环境
- 构建系统: 无（stb 风格单头文件 C 库，无 configure/make/CMake 构建系统）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 (OHOS toolchain)
- 状态: published

## 软件形态结论
arena 是 tsoding 的 stb 风格单头文件 C 库（arena.h，14,602 字节，2025-04-22 上游 commit ab625dd3）。
无构建系统、无 configure/make/CMake/meson 入口、无 test 目录、无 TEST_CASE、无 ctest/注册清单。
消费者在包含前定义 `ARENA_IMPLEMENTATION` 即获得实现。默认后端 ARENA_BACKEND_LIBC_MALLOC
（纯 C 标准库，OHOS 上直接可用；LINUX_MMAP/WIN32/WASM 后端按目标平台条件编译）。

## 编译步骤
1. `init-build arena 20260923 --url=https://github.com/tsoding/arena/archive/refs/heads/master.tar.gz`
   （官方 GitHub archive URL；nested-source 检测无构建文件属预期）
2. `lang-preflight`: detected=c, task=cpp（c↔cpp 兼容族，通过）
3. Step2 编译验证（无构建系统，直接编译示例 + staging）:
   ```bash
   clang -std=c99 -Wall -Wextra -O2 -o test_001 main.c   # examples/001_basic_usage
   ./test_001    # RC=0: "-- sprintf --" / "Foo, Bar, 69, 420.133700" / "Hello, World"
   mkdir -p $TEST_PREFIX/include && cp arena.h $TEST_PREFIX/include/
   clang -std=c99 -I$TEST_PREFIX/include -O2 -o test_001_staged main.c && ./test_001_staged  # RC=0
   ```
4. `conan-init` → 配方改写为 header-only（package_type=header-library, no_copy_source,
   无 build 伪造日志 R34，`copy arena.h → package_folder`, includedirs=["."]）
5. `conan-verify` → G1/G2/G3/G4 + L2/L4/L5 全部 PASS（conan create 干净构建通过，
   test_package 真实调用 arena_alloc/arena_sprintf/arena_reset/arena_free）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 报"下载内容是 HTML" | 任务 URL 是仓库页而非 tarball | 使用官方 archive/refs/heads/master.tar.gz（不可用 tag，仓库无 release tag） |
| 2 | conan-init 生成 autotools 模板 | 默认模板假设有 configure 构建系统 | 改写为 header-only 配方（对齐框架 args-parser 等已验证模式） |
| 3 | G1 配方完整性 FAIL | G1 静态检查要求文本含 build()/export_sources/apply_conandata_patches | 补上这些方法（build 为空实现，无伪造日志） |
| 4 | G2 conan create FAIL: package 无 include | copy(dst="include") 在 header-only + no_copy_source 下未落盘到 package 根 | 对齐 args-parser 模式：dst=package_folder + includedirs=["."] |
| 5 | 010 样例 wasm 构建失败 | 本机 clang 无 wasm32/wasm64 target（样例的 wasm 专用部分） | 非阻塞：native 部分构建运行成功；wasm 部分属样例演示的 wasm 目标，不纳入本包交付 |

## 上游测试完整枚举台账（R51 申报）

**统计口径说明**：arena 是 stb 风格单头文件库，上游**没有任何测试声明/测试框架/测试入口**
（无 tests/ 目录、无 TEST_CASE 宏、无 ctest -N/meson test --list 注册项、无 make check）。
按 R51 清点证据：完整文件清单见下方逐项台账。

| 入口 | 类型分类 | 是否独立上游用例 | 是否实际运行 | 结果 |
|------|----------|------------------|--------------|------|
| arena.h（根目录） | 库本体源码（单头文件，14,602B） | 否（库源码，非测试） | — | — |
| examples/001_basic_usage/main.c | 样例/演示程序（stdio 输出演示） | 否（样例，非 TEST_CASE） | 是 | RC=0，输出符合预期 |
| examples/001_basic_usage/arena.h | 样例内嵌头文件副本 | 否（副本） | — | 与根 arena.h 一致 |
| examples/010_universal_code_wasm_x86_64/expr.c | 样例（表达式解析器演示，native+wasm 双目标） | 否（样例，非 TEST_CASE） | 是（native） | native RC=0（AST 解析输出正常） |
| examples/010_universal_code_wasm_x86_64/nob.c | 样例构建脚本（nob 构建器） | 否（构建脚本） | 是（native 部分） | native 构建成功；wasm 目标因本机 clang 无 wasm target 失败（样例 wasm 专用部分，非本包交付范围） |
| examples/010_universal_code_wasm_x86_64/expr32.wasm / expr64.wasm | 样例 wasm 产物 | 否（未生成） | 尝试构建 | 失败：`No available targets are compatible with triple "wasm32"`（本机 clang 缺 wasm 后端） |
| thirdparty/nob.h | 第三方工具头（nob 构建器库） | 否（工具头，非测试） | — | — |
| thirdparty/stb_sprintf.h | 第三方工具头（stb_sprintf） | 否（工具头，非测试） | — | — |
| examples/010_.../stb_sprintf.h | 样例内嵌工具头副本 | 否（副本） | — | — |
| README.md Quick Start 代码 | 文档中的示例代码 | 否（文档样例） | 是（等价于 001 用例逻辑） | RC=0 |

**统计（双口径）**：
- source_declared_total = 0（上游无可复制枚举的独立 TEST_CASE/测试声明）
- configured_executable_total = 0（无测试注册清单可实例化）
- executed_passed_total = 0；失败 0；未运行/未实例化 0
- 通过率：0/0 不适用（无上游测试）；样例程序 2/2 实际运行通过
- 申报结论：上游确无测试（附清点证据如上），符合 R51 "上游确无测试"须附清点证据要求

## W2/W3 与基线隔离审计

**W3 基线隔离复验**（首次 full 口径命中其他库既有基线文件）：
- 命中路径与隔离前 SHA-256：
  - `archives/c/cloog/0.21.1/.staging-verified` → e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（空文件）
  - `archives/k/kics/2.1.20/.staging-verified` → e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（空文件）
- 隔离方式：不使用 full 全仓口径（会误扫 main 上其他库历史垃圾），改用 `JUNK_PR_DIFF=pr.diff` 单包口径（pr.diff 只含本库 archives/a/arena/**）
- rerun_command: `JUNK_PR_DIFF=pr.diff python3 scripts/ohc-run.py finish arena 20260923 published`（W3 build_and_test.sh）
- rerun_exit_code: 0（JC_RESULT=pass）
- restore_command: 无需恢复——未对上述文件做任何修改/隔离（git diff HEAD 为空）
- 恢复后 SHA-256：同隔离前（e3b0c44...，未改动）
- pre_sha256 == post_sha256 ✅；本库 diff/staged/pr.diff 均不含该两条路径 ✅
- 结论：W3 唯一首错为其他库既有基线文件，隔离复验通过后继续交付

**W2 原子性**：✅ 无框架/基线 diff（仅 archives/a/arena/20260923/** 变更）

## 知识候选台账与路径决定（knowledge-reuse-governance）

**候选 C1**：无 include/ 子目录、头文件位于源码根目录的单头文件 C 库（stb 风格，
ARENA_IMPLEMENTATION 消费者模式）的 Conan 配方形态
- 真实错误：conan-init 生成 autotools 模板 → conan create 失败；copy(dst="include") 后
  test_package 配置期报 "Imported target arena::arena includes non-existent path .../p/include"
- 根因：无构建系统 + basic_layout 路径语义 + G1 硬性要求 build()/export_sources()/
  apply_conandata_patches 声明（即使无补丁）
- 修复：header-only 配方（package_type=header-library, no_copy_source）+ 三方法显式声明 +
  copy 到 package_folder 根 + cpp_info.includedirs=["."]（无 include/ 子目录时走包根）
- 验证：conan-verify G1-G4+L2/L4/L5 全 PASS；test_ohos T1-T7 全 PASS；消费者 test_package 通过
- 适用范围：所有"头文件在源码根、无 include/ 子目录"的纯 C 单头文件库
- 四范围查重：doc/（E257 no-op build、E470/E321/E322 header-only 配方、E311 source 隔离）
  部分覆盖；graph/ 部分覆盖；drafts/（DRAFT-cobs-c 无构建系统纯 C、DRAFT-boost-te copy
  绝对路径、DRAFT-enet stb 风格）部分覆盖；正式图谱部分覆盖
- 新增差异：既有条目均走 include/ 子目录形态（copy 到 include/ + includedirs=["include"]），
  未覆盖"无 include/ 子目录 → copy 到包根 + includedirs=["."]" 的根目录形态；
  ARENA_IMPLEMENTATION 消费者测试模式亦无既有条目
- 七轴：exact_duplicate=false, causal_duplicate=false（部分覆盖）, trigger_overlap=true（G1 门禁同源）,
  solution_overlap=partial（包根形态新增）, combination_novelty=true, boundary_novelty=true,
  test_migration_novelty=true（ARENA_IMPLEMENTATION 消费者用例）
- 查重决定：**new_draft**（新增差异已由本轮 conan-verify + test_ohos 真实日志验证，可跨库复用）

**候选 C2**：W3/finish 全仓 junk_check 命中其他库既有基线垃圾（cloog/kics .staging-verified）
- 修复：JUNK_PR_DIFF=pr.diff 单包口径（pr.diff 只含本库路径），隔离复验后 W3 通过
- 查重：drafts/ 已有 DRAFT-fastnoiselite-jc-full-mode-baseline-junk-isolation、
  DRAFT-libfort、DRAFT-libpopcnt 完全覆盖同根因同方案 → **exact_duplicate=true，
  reuse_existing**（复用既有草稿，不新建）

**候选 C3**：conan-verify E017 镜像注入残留 conandata.yml.ghfast-bak/.orig → 提交前清理
- 查重：doc/E017（use-ghfast）+ E415（conandata.yml.orig 残留恢复）完全覆盖 → reuse_existing

**候选 C4**：OHOS python3 subprocess 无法按 PATH 解析裸命令（posix_spawn 不搜索 PATH）→ shutil.which
- 查重：doc/E055/E405 + drafts/ DRAFT-4033-binwalk、DRAFT-apertium 完全覆盖 → reuse_existing

**候选 C5**：上游无任何测试声明的单头文件库 R51 申报（source_declared_total=0）
- 属标准申报流程，非知识条目 → path_a_no_knowledge（无知识沉淀）

**路径决定：Path B（知识库扩展）**——C1 有验证过的跨库新增差异，建立同 stem 草稿
DRAFT-arena-20260923-pure-c-header-only-root-include-recipe(.md/.kv)；
C2-C4 复用既有知识；C5 无知识。

## 依赖版本
- 无外部依赖（纯 C 标准库，依赖 0 个）

## 验证结果
```bash
conan-verify arena 20260923   # G1/G2/G3/G4+L2/L4/L5 全部 PASS
./test_001                    # RC=0
./build/expr.native           # RC=0
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| archives/a/arena/20260923/conanfile.py | header-only 配方 | package_type=header-library |
| archives/a/arena/20260923/conandata.yml | sha256=2aefa7aab... | 官方 GitHub archive URL |
| archives/a/arena/20260923/test_package/ | 消费者测试 | 真实调用 arena API（R34） |
| archives/a/arena/20260923/manifest.yaml | 元数据 | 见 manifest.yaml |
| archives/a/arena/20260923/reports/conan-verify-report.md | 验证报告 | G1-G4+L2/L4/L5 PASS |
---

**编译结束**: 2026-09-24 09:42
**最终状态**: published
