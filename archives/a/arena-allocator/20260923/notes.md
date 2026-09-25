# arena-allocator 20260923 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile 仅构建 tests/examples；库本体为单头文件）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 (llvm-15 release)
- 状态: built

## 编译步骤

```bash
export CC=clang TMPDIR=$HOME/tmp
# 上游测试：make tests && ./test（5 用例 / 4 suite 全通过）
# 上游示例：make example example_aligned example_debug（三个示例运行正常）
# Conan 配方：header-only（package_type=header-library，无编译步骤）
# conan-verify G1-G4 全通过（conan create 干净构建通过）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | arena.c / rktest.h / rktest.c 结尾缺换行，clang `-Werror -Wnewline-eof` 编译失败 | 上游源文件无文件尾换行 | 补文件尾换行（仅换行，无逻辑改动；track-edit 记录） |
| 2 | init-build 直连 github.com 下载返回 HTML | 本机网络对 github.com 直连受限（API/codeload 可达） | 经 codeload 下载官方 main HEAD commit ddd313d tarball 放入构建缓存 |
| 3 | conan create 报 "Package type is 'library', but no 'shared' option declared" | 单头文件库误用 library 类型 | 改为 header-library 类型 |
| 4 | test_package 报 include 路径不存在 | copy() dst 用相对路径 | 按仓库既有配方改用 os.path.join(package_folder, "include") |

## 源码修改

- arena.c / rktest.h / rktest.c：仅补文件尾换行符（无逻辑修改），track-edit 记录；
  header-only 打包不引入补丁（patches 清空），修复仅用于本地测试编译与文档证据。

## 依赖版本

- 无第三方依赖（header-only，C 标准库）

## 验证结果

```bash
# 上游测试（rktest 框架，tests.c 5 个 TEST 用例 / 4 suite）
$ ./test
[==========] Running 5 tests from 4 test suites.
[  PASSED  ] 5 tests.

# 上游示例
$ ./example && ./example_aligned && ./example_debug   # 输出正常

# 消费者验证（test_package）
$ conan create ...   # G2 通过，test_arena-allocator 运行 OK

# 鸿蒙专项测试
$ ./test_ohos   # 全部断言通过
```

# 鸿蒙专项测试（追加，独立于上游 tests.c）

新增 test_ohos.c（真实调用公开 API：arena_create/arena_alloc/arena_alloc_aligned/
arena_copy/arena_clear/arena_destroy），在 OHOS PC (arm64) 环境编译运行：
17/17 断言全部通过（含 16 字节对齐可观察结果、arena_copy 覆盖语义、clear 后复用）。

```bash
$ clang -std=gnu11 -fPIC -O2 -Wall -Wextra -o test_ohos test_ohos.c test_ohos_impl.c
$ ./test_ohos
== 结果: 全部通过 (0 失败) ==
```

## 上游测试台账（双口径）

源码声明总数（source_declared_total）: 5 （tests.c 中独立的 rktest TEST() 用例）
当前配置实际执行并通过（executed_passed_total）: 5
未实例化: 0
执行通过率: 5/5 (100.0%)

逐项映射:
1. arena_init_tests.init — tests.c TEST() → ./test 注册 → 运行 OK
2. arena_create_tests.basic — tests.c TEST() → ./test 注册 → 运行 OK
3. arena_create_tests.zero_bytes — tests.c TEST() → ./test 注册 → 运行 OK
4. arena_alloc_tests.basic — tests.c TEST() → ./test 注册 → 运行 OK
5. arena_alloc_aligned_tests.edge_case_tight_space — tests.c TEST() → ./test 注册 → 运行 OK

分类说明:
- rktest.h/rktest.c: 上游测试框架（宏/实现），非独立用户用例，不计入分母
- code_examples/example*.c: 上游示例（非测试），已编译运行验证，不计入用例数
- arena.h: 库本体头文件（非测试）
- valgrind: 设备上无 valgrind，Makefile `test` 目标的 valgrind 包装无法执行，
  已直接运行 test 二进制完成全部用例验证（该入口本身非独立用例，仅包装层）

## 知识候选台账（knowledge_candidate_ledger）

### 候选 C1: clang -Werror -Wnewline-eof 拦截上游缺文件尾换行
- 真实错误: `error: no newline at end of file [-Werror,-Wnewline-eof]`（arena.c/rktest.c/rktest.h 三个源文件）
- 根因: 上游 C 源文件缺少文件尾换行符，clang 在 `-Werror -Wall -Wextra -pedantic` 下把 -Wnewline-eof 升级为错误
- 修复: 仅补文件尾换行符（无逻辑改动），track-edit 记录
- 验证: make tests 编译通过，5/5 上游测试全过；conan create G2 通过
- 适用: 所有以 -Werror 编译的 C/C++ 库（上游 Makefile/CMake 启用严格告警时）
- 查重:
  - exact_duplicate: false（index.tsv 无 newline/Wnewline-eof 条目）
  - causal_duplicate: false（无同类根因条目）
  - trigger_overlap: false（触发工具 clang/编译告警，图谱无同类）
  - solution_overlap: false（补换行方案无既有条目）
  - combination_novelty: true（新增差异：-Werror -Wnewline-eof 触发面 + 最小补丁）
  - boundary_novelty: true（适用于所有 C/C++ 库而非特定库）
  - test_migration_novelty: false（无测试迁移维度）
- 关系: similar_to=none; caused_by=none; prerequisite_of=none; conflicts_with=none
- 决定: new_draft（新建 DRAFT-arena-allocator-newline-eof 草稿 + .md 配对）

### 候选 C2: 单头文件 C 库 → header-library 配方（package_type + copy 绝对路径）
- 真实错误: `Package type is 'library', but no 'shared' option declared` + `Imported target includes non-existent path .../p/include`
- 根因: 单头文件库（无 configure/install）误用 library 类型；copy() 相对 dst 被解析到 build 目录
- 修复: package_type=header-library；copy() dst 用 os.path.join(package_folder, "include")
- 验证: conan create G2 通过，test_package 消费者验证 OK
- 查重:
  - exact_duplicate: false
  - causal_duplicate: false
  - trigger_overlap: true（与 E283 library/shared 契约同触发）
  - solution_overlap: true（E283 declare-shared-contract / E321 header-only-lite / boost-te 草稿 copy 绝对路径均覆盖）
  - combination_novelty: false（无新增差异，既有条目已覆盖）
  - boundary_novelty: false
  - test_migration_novelty: false
- 关系: similar_to=E283, E321, DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental
- 决定: reuse_existing（复用 E283/E321/boost-te 草稿，不新建）

### 候选 C3: W3 junk_check full 模式扫到 main 上其他库历史垃圾
- 真实错误: JC5 fail，命中 archives/c/cloog/0.21.1/.build-closed 等 main 存量文件
- 根因: 本地零提交时 junk_check 回退 full 模式（git ls-files 整仓扫描），而真实 CI 走 pr.diff 模式
- 修复: 生成单包 pr.diff（JUNK_PR_DIFF），junk_check 转 prdiff 模式；清理本包 conandata.yml.ghfast-bak 与 CMake 构建产物
- 验证: W3 本地 CI 模拟通过
- 查重:
  - exact_duplicate: false
  - causal_duplicate: false
  - trigger_overlap: true（与 boost-te 草稿 W3 full 模式基线噪声同触发）
  - solution_overlap: true（boost-te 草稿 commit-first 方案同族；本包用 JUNK_PR_DIFF 单包口径等价规避）
  - combination_novelty: false
  - boundary_novelty: false
  - test_migration_novelty: false
- 关系: similar_to=DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental
- 决定: reuse_existing（复用 boost-te 草稿，不新建）

### 路径决定
- 候选 C1 已验证、可跨库复用、查重未命中 → new_draft → 路径 B（知识库扩展）
- 候选 C2/C3 既有条目/草稿已覆盖 → reuse_existing
- 最终: 路径 B，同一 PR 携带 DRAFT 草稿（.kv/.md 配对）与三方库归档

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only Conan 配方（package_type=header-library） |
| conandata.yml | 官方 main HEAD ddd313d 归档 URL + SHA-256 |
| test_package/ | 消费者测试（真实调用公开 API）+ MANIFEST |
| reports/ | conan-create.log、conan-verify-report.md |
---

**编译结束**: 2026-09-24 04:17
**最终状态**: built
