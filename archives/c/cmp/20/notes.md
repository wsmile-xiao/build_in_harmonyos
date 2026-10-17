# cmp 20 适配笔记

## 编译环境
- 构建系统: custom (无正式构建系统，README: "There is no build system for CMP"，提供 Makefile 仅供测试/示例)
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18)
- 目标: aarch64-linux-ohos (armv8 / OHOS 6.0)
- 状态: built

## 源码来源
- 官方上游: https://github.com/camgunz/cmp (tag v20, 2022-03-30)
- 下载: https://codeload.github.com/camgunz/cmp/tar.gz/refs/tags/v20
- SHA-256: cde6db84cb04913d4ce4880c4db665555f92c163f362de151e350d8f30113362
- 说明: 任务声明上游为 github.com/camgunz/cmp；search-url 建议的 waterlan.home.xs4all.nl 已随 XS4ALL 主页下线返回 404，实测不可用，改用 GitHub 官方 tag。

## 编译步骤

cmp 是纯 C 单文件库（cmp.c + cmp.h，C89），无 configure/cmake 构建系统，直接编译源码即可：

```bash
# 库编译（C89，严格告警）
clang -c cmp.c -o cmp.o -std=c89 -Wno-c99-extensions -I. \
  -Wall -Wextra -funsigned-char -fwrapv -Wconversion -Wno-sign-conversion \
  -Wpointer-arith -Wformat-nonliteral -Winit-self -Wwrite-strings \
  -Wshadow -Wenum-compare -Wempty-body -Wparentheses -Wcast-align \
  -Wstrict-aliasing --pedantic-errors -Wno-error=deprecated-declarations -O2
# → exit 0，无错误
```

Conan 配方将库编译为静态库并安装头文件（见 conanfile.py）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 SSL CERTIFICATE_VERIFY_FAILED | Python urllib 走系统代理时无法校验证书链 | 以 curl 同款 CA bundle（/etc/ssl/certs/cacert.pem）设置 SSL_CERT_FILE 重跑 init-build |
| 2 | cmp.h 中 `_Bool` 报 C99 扩展错误 | -std=c89 下 clang 严格模式 | 按上游 Makefile 约定加 -Wno-c99-extensions |
| 3 | test/test.c 无法编译/链接（unit_test/run_tests 未定义） | 上游测试面向旧版 cmocka API；本仓制品 cmocka 2.0.2 移除了 UnitTest/unit_test/run_tests 旧 API | 将 test.c main() 迁移到新 API：cmocka_unit_test + cmocka_run_group_tests_name；编译时加 -DCMOCKA_DISABLE_DEPRECATION_WARNINGS 展开旧宏 |
| 4 | MSan 变体 cmpmemtest 链接失败 | OHOS clang 15 工具链未提供 libclang_rt.msan.a | 平台工具链限制，MSan 变体不可链接；如实记录，其余变体（普通/UBSan/ASan/nofloat）全部通过 |

## 源码修改

test/test.c：main() 从旧 cmocka API（UnitTest 数组 + run_tests）迁移到新 API（struct CMUnitTest 数组 + cmocka_run_group_tests_name）。这是纯 API 兼容适配，无平台宏。由 refresh-patch 生成补丁文件。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| cmocka | 2.0.2 (ohpcd 制品仓, rev 07881f2c) | 上游测试框架（test_requires，非运行依赖） |

## 上游测试台账（双口径）

### 源码声明测试入口枚举

| 文件 | 类型 | 独立上游用例? | 说明 |
|------|------|--------------|------|
| test/test.c | 用户测试源（main） | 是（注册器） | 注册 17 个用例（CMP_NO_FLOAT 下 16 个，test_float_flip 被条件排除） |
| test/tests.c | 用户测试源（用例实现） | 是（17 个用例实现） | 17 个 void test_*(void**state) 函数；共 1557 个断言宏 |
| test/buf.c / buf.h | 测试辅助 | 否 | 内存 buffer 辅助实现 |
| test/utils.c / utils.h | 测试辅助 | 否 | 工具函数（随机数据等） |
| test/profile.c | 基准程序 | 否 | cmocka 基准入口（cmpprof），依赖 libprofiler，非用例 |
| test/cases.mpac | fixture 数据 | 否 | MessagePack 用例数据文件 |
| examples/example1.c | 示例 | 否 | 示例程序（编译+运行验证） |
| examples/example2.c | 示例 | 否 | 示例程序（编译+运行验证） |
| examples/cmp_data.dat | 示例数据 | 否 | 示例数据 |
| CMakeLists.txt | ESP-IDF 组件声明 | 否 | register_component()，非本平台构建入口 |
| Makefile | 构建目标声明 | 否 | 测试构建目标：cmpunittest/cmpnofloattest/cmpaddrtest/cmpmemtest/cmpubtest/cmpprof/example1/example2 |

### 双口径统计

- source_declared_total = **17**（test.c 注册的全部独立用例，含 CMP_NO_FLOAT 条件用例 1 个）
- configured_executable_total = **17**（当前配置实际注册的独立可执行用例；nofloat 变体 16）
- 实际运行与结果（OHOS aarch64 真机环境）：

| 变体 | 用例数 | 结果 | 日志 |
|------|--------|------|------|
| cmpunittest（普通） | 17 | 17/17 通过 (100%) | logs/cmpunittest-run.log |
| cmpubtest（UBSan） | 17 | 17/17 通过 (100%) | logs/cmpubtest-run.log |
| cmpaddrtest（ASan） | 17 | 17/17 通过 (100%) | logs/cmpaddrtest-run.log |
| cmpnofloattest（CMP_NO_FLOAT） | 16 | 16/16 通过 (100%) | logs/cmpnofloattest-run.log |
| cmpmemtest（MSan） | 17 | 不可链接（平台工具链缺 libclang_rt.msan.a） | — |
| example1 / example2 | — | 编译+运行成功 | logs/example1-run.log, logs/example2-run.log |

- executed_passed_total / source_declared_total = **17/17 (100%)**（普通配置）
- executed_passed_total / configured_executable_total = **17/17 (100%)**（可执行集合）
- 未运行/未实例化：0（MSan 变体属同一用例集在不同消毒器配置下的构建，因工具链缺 MSan 运行时不可链接，非独立用例缺失；恢复条件 = 工具链提供 libclang_rt.msan.a）

### 映射（声明 → 注册 → 执行）
- 源码声明：test/tests.c 内 `void test_*(void**state)` 17 个实现 + test/test.c 的 `cmocka_unit_test()` 注册 17 项
- 条件分支：`#ifndef CMP_NO_FLOAT` 排除 test_float_flip（nofloat 变体 16 项）
- 构建目标：clang 直接编译 test.c/tests.c/buf.c/utils.c + cmp.c，链接 -lcmocka
- 执行：真机直接运行 cmpunittest/cmpubtest/cmpaddrtest/cmpnofloattest，全部 [PASSED]

## 验证结果

```bash
# 全部通过（见上表，4 个可链接变体 100% 通过，MSan 平台限制）
# 库编译：cmp.c C89 严格模式 exit 0
```

## 知识候选（观察，正式查重见 knowledge/graph 流程）
1. cmocka 2.x 移除旧 API（UnitTest/unit_test/run_tests）后，面向旧 API 的上游测试 main 需要迁移到 cmocka_unit_test + cmocka_run_group_tests_name；编译期需 -DCMOCKA_DISABLE_DEPRECATION_WARNINGS 才能展开旧宏。适用于所有用旧 cmocka API 写测试的三方库在鸿蒙 PC 的适配。
2. OHOS SDK clang 15 未随附 libclang_rt.msan.a（MemorySanitizer 运行时缺失），MSan 变体无法链接；ASan/UBSan 可用。适用于鸿蒙 PC 上任何需要 MSan 构建的三方库。
---

**编译结束**: 2026-09-06 23:05
**最终状态**: built

## 基线隔离审计 (baseline_isolation_audit)

W3/finish 期间 JC5 唯一命中的是其他库基线文件（提交前已存在于 main，非当前库文件）：

- path: archives/u/util-linux-login/2.42.2/.ci-trigger
- pre_sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- isolation_command: `git rm --cached archives/u/util-linux-login/2.42.2/.ci-trigger`（索引级隔离；JC5 基于 git ls-files 扫描，磁盘级隔离无效）
- rerun_command: `python3 scripts/ohc-run.py finish cmp 20 built`
- rerun_exit_code: 0（W3/JC5 通过，finish 继续至 step 8）
- restore_command: `git add -f archives/u/util-linux-login/2.42.2/.ci-trigger && git ls-files <path>`（该路径被 .gitignore 忽略，需 -f 恢复索引）
- post_sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- pre_sha256 == post_sha256: 是
- 当前库 diff/staged/PR 包含该路径: 否（git status 该路径 clean，无 staged 变更）
- 结论: 隔离复验通过，该文件未修改、未提交、未写入知识库/PR；继续 cmp 交付

说明: 本地 W3 在分支尚无 commit 时以 full 模式（git ls-files 全仓）扫描，命中该基线；远端 CI 以 PR diff 模式仅扫描本次 PR 文件，不会包含该路径。

## 知识候选台账 (knowledge_candidate_ledger) 与七轴查重

### 候选 1: cmocka 2.x 移除旧 API（unit_test/run_tests）的上游测试迁移
- 真实错误: test/test.c 用旧 API（UnitTest 数组 + run_tests），cmocka 2.0.2 下编译错误 + 链接 undefined symbol: run_tests
- 根因: cmocka 2.x 删除 run_tests；旧宏 unit_test 需 -DCMOCKA_DISABLE_DEPRECATION_WARNINGS 展开
- 修复: main() 迁移到 cmocka_unit_test + cmocka_run_group_tests_name（见 patches/）
- 验证: 编译链接成功，17/17 用例通过（3 种消毒器配置）
- 适用范围: 任何用旧 cmocka API 写测试入口的 C/C++ 库在 OHOS PC 适配
- 查重:
  - `exact_duplicate`: false（E531 是 qsort_r，E269/E410 是 Python run_tests，均无关）
  - `causal_duplicate`: false
  - `trigger_overlap`: false（编译期 API 语法，与既有条目触发面不同）
  - `solution_overlap`: false
  - `combination_novelty`: true（cmocka 2.x API 迁移 × OHOS PC 组合，无既有条目）
  - `boundary_novelty`: true（严格 C99 下 deprecated 宏展开边界）
  - `test_migration_novelty`: true（迁移上游测试入口而非跳过）
- 关系: similar_to [E531]（同为 cmocka 相关但不同面）；caused_by/prerequisite_of/conflicts_with: 无
- 决定: **new_draft** → knowledge/drafts/DRAFT-cmp-20-cmocka2-api-migration.kv/.md

### 候选 2: OHOS SDK clang 15 缺 libclang_rt.msan.a（MSan 变体无法链接）
- 真实错误: cmpmemtest 链接失败 ld.lld cannot open libclang_rt.msan.a
- 根因: OHOS SDK 26.0.0.18 工具链 lib 未随附 MSan 运行时；ASan/UBSan 运行时齐全
- 修复: 无代码修复；如实记录平台限制 + ASan/UBSan 变体覆盖消毒器验证
- 验证: 链接失败日志 + asan/ubsan 变体 17/17/16 通过
- 适用范围: OHOS PC 上任何声明 -fsanitize=memory 测试变体的三方库
- 查重:
  - `exact_duplicate`: false（musl-glibc-developer-impact.md 仅概述"需 musl 适配"，未记链接失败）
  - `causal_duplicate`: false
  - `trigger_overlap`: 低（sanitizer/llvm 测试面，E387 是 lit 工具链问题）
  - `solution_overlap`: 低
  - `combination_novelty`: true
  - `boundary_novelty`: true（工具链 lib 目录精确边界）
  - `test_migration_novelty`: 中（不改测试仅分类）
- 关系: similar_to [E387]; 其余无
- 决定: **new_draft** → knowledge/drafts/DRAFT-cmp-20-ohos-msan-runtime-missing.kv/.md

### 候选 3: codeload BadZipFile → get() 显式 filename
- 真实错误: conan create source() 报 BadZipFile: File is not a zip file
- 根因: codeload URL basename 为 tag 名无扩展名，conan 误用 zip 解码器
- 修复: source() 中 get(..., filename="cmp-20.tar.gz")（与 E276/E392/E483 方案一致）
- 查重: exact_duplicate=true（E276 同因同解，E392/E483 扩充 raw makefile 场景）
- 决定: **reuse_existing**（复用 E276/E392/E483，不新建草稿）

### 候选 4: 无构建系统单文件库直接编译配方
- 真实错误: 无（配方一次通过）；做法与 E392 raw-makefile-conan-recipe-pattern 同族
- 查重: solution_overlap=true（E392 已覆盖 raw makefile/single-file 配方的绝对路径与 cwd 要点）
- 决定: **reuse_existing**（复用 E392，不新建草稿）

### 路径判定
- new_draft 候选 2 项（cmocka API 迁移、MSan 运行时缺失），均已由本轮真实日志验证、
  可跨库复用、查重未命中或部分覆盖且存在新增差异 ⇒ **路径 B：知识库扩展**
- PR 前缀: 【知识库扩展】（任务头 initial_pr_prefix 一致）
- 草稿与三方库归档同 PR 交付（knowledge/drafts/DRAFT-cmp-20-*.kv/.md + archives/c/cmp/20）
