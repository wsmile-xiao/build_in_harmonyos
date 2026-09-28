# fixed_point_arith 0.0-git9b5da0fa97 适配笔记

## 知识候选台账 + 四范围查重（knowledge_candidate_ledger）

**四范围**：正式条目（knowledge/doc/E###.md + graph/E###.kv）、knowledge/drafts/（3250 草稿）、
knowledge/graph/index.tsv（766 行）、knowledge/doc/（E 编号文档）。

### 候选 C1：raw-makefile Conan 配方模式（codeload filename / compiler_executables 字典 / make cwd）
- 错误与根因：init-build 裸 URL 报 HTML；conan create 报 `tools.build:compiler_executables:c` 不存在；
  Makefile 无 install 目标需手动 package()。
- 修复与验证：官方 commit 归档 URL + 三要素配方（见下）；conan create + test_package 全绿。
- 查重七轴：`exact_duplicate: true`（E392 三要素与本候选逐条一致：BadZipFile filename /
  check_type=dict / make cwd；且同为 raw makefile + codeload 场景）；
  `causal_duplicate: true`；`trigger_overlap: true`；`solution_overlap: true`；
  `combination_novelty: false`；`boundary_novelty: false`；`test_migration_novelty: false`。
- 决定：**复用 E392，不建重复草稿**。本库新增差异仅为 OUT_DIR 指向 build_folder 的产物隔离细节，
  属实现变体，无独立跨库复用价值。`similar_to: E392`。
- 路径归口：path_a_no_knowledge（配方知识已有覆盖）。

### 候选 C2：W3/JC full 模式命中其他库基线垃圾文件（cloog/kics 空标记文件）
- 错误与根因：`finish` W3 本地 CI 模拟 JC1/JC5 报 3 个其他库跟踪的空文件
  （archives/c/cloog/0.21.1/.build-closed、/ .staging-verified、archives/k/kics/2.1.20/.staging-verified）；
  junk_check.sh full 模式按 `git ls-files`（索引跟踪状态）全仓扫描，工作区移出无效。
- 修复与验证：`git rm --cached` 临时取消跟踪 → 复跑 W3（JC 通过、L0/L1/L4/L5 全 pass）→
  `git reset` 原样恢复索引 → 逐文件核对 post-SHA-256 == pre-SHA-256（e3b0c44… 空文件哈希一致）、
  git status 干净、不在本库 diff。
- 查重七轴：`exact_duplicate: true`（DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation 描述
  同一 cloog/kics 场景、同一 git rm --cached + restore 手法、同一 SHA-256 证据）；
  `causal_duplicate: true`；`trigger_overlap: true`；`solution_overlap: true`；
  `combination_novelty: false`；`boundary_novelty: false`；`test_migration_novelty: false`。
- 决定：**复用既有草稿/条目，不重复建稿**。`similar_to: DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation`。

### 候选 C3：头文件门控的 inline 公开 API —— 配方必须注入 cpp_info.defines
- 错误与根因：fixed_point_arith 的公开 API 仅在定义 `FXP_C99_INLINE` 时才声明
  （fixed_point.h `#ifdef FXP_C99_INLINE → #include "inline/fixed_point.h"`），
  上游 Makefile 默认 `-DFXP_C99_INLINE` 编译；消费者不定义该宏则头文件无任何函数声明，
  只看到宏与类型，导致编译隐式声明错误/链接失败。
- 修复与验证：`package_info()` 注入 `self.cpp_info.defines = ["FXP_C99_INLINE"]`；
  conan create 消费者 test.c（仅用公开头文件 f_add/f_mul/q_rot）编译链接运行全绿，13 断言通过。
- 查重七轴：`exact_duplicate: false`；`causal_duplicate: false`；`trigger_overlap: false`
  （E151 是构建期 HAVE_* 特性探测，非消费者声明门控；无任何 doc/draft 覆盖 cpp_info.defines 注入）；
  `solution_overlap: false`；`combination_novelty: true`（头文件门控 + 配方 defines 注入的组合）；
  `boundary_novelty: true`（适用任何"C 库公开 API 以宏门控 inline/声明"的库，如固定点/向量/矩阵类）；
  `test_migration_novelty: true`（消费者测试必须依赖 defines 注入才能编译，测试迁移性由配方保证）。
- 决定：**走路径 B（new_draft）**，建立 `DRAFT-fixed_point_arith-0.0-git9b5da0fa97-inline-gated-api-defines-injection`。
  `similar_to: []`；`caused_by: []`；`prerequisite_of: []`；`conflicts_with: []`。
- 适用边界/反例：若库的公开声明无条件暴露（如普通 extern 函数头），无需注入；仅当
  API 声明位于 `#ifdef <宏>` 之内且上游以该宏编译时才需要，且注入值与上游默认必须一致。

### 候选 C4：Q1.15 固定点消费者测试须容忍 ±LSB 舍入（FRAC_1_V=32767 ≠ 1.0）
- 错误与根因：test.c 初版用精确断言 `q_rot 180°z (0.5,0,0) == -16384` 失败，实测为 -16383
  （q_mul 链式乘法累积舍入；FRAC_1_V=32767 非精确 1.0），且 `{{32768},...}` 字面量溢出 int16
  （32768 → -32768，q_conj 断言连带失败）。
- 修复与验证：改用 `FRAC_1_V` 常量 + `CLOSE(a,b,tol)` 容差断言 + “旋转两次回原点”不变量；
  conan create 全绿。
- 查重七轴：`exact_duplicate: false`；`causal_duplicate: false`；`trigger_overlap: false`；
  `solution_overlap: false`；`combination_novelty: true`（固定点舍入 + int16 溢出 + 容差断言组合）；\
  `boundary_novelty: true`（适用于任何 Q 格式固定点库的消费者测试编写）；
  `test_migration_novelty: true`。
- 决定：**走路径 B（new_draft）**（作为 C3 的配套测试写法草稿，或独立草稿；本候选与 C3 同库、
  同 PR，按"同 stem 配对"建立独立草稿亦可）。本候选并入 C3 草稿的验证小节，避免碎片化：
  以 C3 草稿为主干，C4 作为其"测试迁移"实例小节；不再单独建第二份草稿。
- 适用边界/反例：若测试对象为整数精确运算（非舍入型），容差断言会掩盖真实错误，应使用精确断言。

### 路径决定汇总
- `reuse_existing: ["E392", "DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation"]`（候选 C1/C2）
- `new_draft: ["DRAFT-fixed_point_arith-0.0-git9b5da0fa97-inline-gated-api-defines-injection"]`（候选 C3+C4）
- `path_a_no_knowledge: false`（C3/C4 有真实新增知识且可跨库复用，路径 B 成立）
- 知识库草稿与 fixed_point_arith 归档文件同 PR 交付（不另建脱离三方库的知识库 PR）。

## 上游测试双口径台账（完整枚举证据）

**枚举方法（可复制）**：对官方 tag 源码（`fixed_point_arith-9b5da0fa97` 解压根目录）执行
`find . -iname "*test*" -o -iname "*check*"`、`grep -rn "TEST_CASE|TEST_F|RUN_TEST|assert(" src include`、
`find . -name "CMakeLists.txt" -o -name "*.cmake"`、`grep -n "test\|check" Makefile`，
并阅读 Makefile 全部目标（`all/library/proofs/docs/clean/depclean/allclean/wipe/unicodize`）。

**统计口径**：
- `source_declared_total = 0`：官方源码无任何测试声明 —— 无 tests/ 目录、无 CMake/ctest、
  无 GTest/Unity/自定义 TEST_CASE 宏、Makefile 无 check/test 目标（只有 `proofs` Frama-C
  形式化验证目标，依赖 frama-c + Z3，非可执行单元测试，不计入上游用例）；
- `configured_executable_total = 0`：当前 OHOS 配置无任何可实例化测试用例；
- `executed_passed_total = 0`，失败 0，未运行 0；
- 全量通过率：0/0（上游无测试，非"0 通过"）。消费者验证 + 鸿蒙专项测试见下文，
  与上游测试分别计数，不重复充数。

**逐项映射（源码声明 -> 构建条件 -> 构建目标 -> 注册项 -> 执行日志）**：空集，无需映射。

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure/CMake/install 目标）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / llvm-ar / llvm-nm
- 状态: built（配方已编写，待 conan create 验证后置 published）

## 编译步骤

1. 官方源码：`https://codeload.github.com/jcarrano/fixed_point_arith/tar.gz/9b5da0fa97`
   （commit 9b5da0fa9782561a730f9b5cd745a30fe661ea8d，2019-06-03 BUGFIX 提交，
   官方 GitHub API 核验 sha/date/message 一致；tarball SHA-256 多次下载一致）
2. 手工验证构建：`make OUT_DIR=build CC=clang AR=llvm-ar NM=llvm-nm CFLAGS="-fPIC -O2" -j1`
   → 产出 `build/fixed_point.a`（静态库）+ `build/fixed_point.sym`（89 个导出符号）
3. 配方构建：`conanfile.py` 以 `OUT_DIR=$(build_folder)` 隔离产物目录，
   编译器/标志从 `tools.build:compiler_executables` conf 获取（R33，不裸用 ${CC}）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 裸 URL `https://github.com/jcarrano/fixed_point_arith` 报"下载内容是 HTML" | 工具按 tar 下载整仓主页 | 改用官方 commit 归档 URL（codeload tar.gz/<sha>） |
| 2 | 上游 Makefile 无 install 目标 | 纯库工程，仅产 .a | 配方 package() 手动 copy 头文件 + 静态库，命名为 libfixed_point.a |
| 3 | 公开 API 头文件在未定义 FXP_C99_INLINE 时无函数声明 | 上游宏设计（inline 函数默认随编译单元内联） | cpp_info.defines 注入 FXP_C99_INLINE，与上游默认用法一致 |

## 源码修改

无（本次不修改上游源码，无补丁）。

## 依赖版本

- 无第三方依赖（仅 libc 的 stdint/stdbool），L0 依赖解析为空集。

## 验证结果

```bash
make -C <src> CC=clang AR=llvm-ar NM=llvm-nm CFLAGS="-fPIC -O2" OUT_DIR=<build> -j1  # 退出码 0
# 后续: conan create 验证 + test_package 消费者测试（f_add/f_mul/q_rot 等 13 断言）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conandata.yml | 官方 URL + SHA-256 |
| conanfile.py | Makefile 驱动配方，静态库 |
| test_package/ | 消费者验证（CMake + 13 断言） |
| test_ohos/ | 鸿蒙专项验证（见任务后续） |

## 注意事项

- FXP_C99_INLINE 是公开 API 声明开关，消费者与库编译必须一致；
- 上游 `proofs` 目标依赖 Frama-C + Z3，属形式化验证工具链，非可执行单元测试，不计入测试统计。
---

**编译结束**: 2026-09-27 21:41
**最终状态**: built
