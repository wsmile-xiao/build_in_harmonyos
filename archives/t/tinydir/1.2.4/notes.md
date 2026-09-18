# tinydir 1.2.4 适配笔记

## 编译环境
- 构建系统: header-only（无编译阶段；上游 samples/tests 为 CMake）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. init-build（官方 tag tarball）
python3 scripts/ohc-run.py init-build tinydir 1.2.4 --url=https://github.com/cxong/tinydir/archive/refs/tags/1.2.4.tar.gz
# ⚠️ 发现 init-build 嵌套提升误判：把 samples/ 提升为源码根，丢失 tinydir.h 与 tests/
#    修复：从官方 tarball 重新解压完整 26 文件到 .orig/.work

# 2. 校验官方源 SHA-256
#    9c50eda69ba4854bb76ffa18961f49fd75f323b4cbebdf6b4b2d2db28f9f5ce2（与官方 codeload 一致）

# 3. conan-init（headeronly 模板）→ 修正 license=BSD-2-Clause、homepage

# 4. 上游测试构建（tests/CMakeLists.txt，CMake 4.x 需策略兼容）
cmake ../tests -DCMAKE_C_COMPILER=clang -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j1 && ctest   # 1/1 通过（file_open_test）

# 5. 鸿蒙专项消费者测试（test_package/test_tinydir_harmonyos.c）
clang -std=c11 -Wall -Wextra -I<src> test_tinydir_harmonyos.c -o test_tinydir_harmonyos
./test_tinydir_harmonyos   # 全部 PASS（28 项断言），aarch64 平台断言

# 6. conan-verify（G1-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-verify tinydir 1.2.4

# 7. finish（W2 结构 + W3 本地 CI 通过，exit_code=0）
python3 scripts/ohc-run.py finish tinydir 1.2.4 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 `https://github.com/cxong/tinydir` 报"下载内容是 HTML" | 裸仓库 URL 返回 GitHub 页面而非 tarball | 改用官方 tag 压缩包 `https://github.com/cxong/tinydir/archive/refs/tags/1.2.4.tar.gz` |
| 2 | init-build 嵌套源码提升把 samples/ 当源码根，丢失 tinydir.h 与 tests/ | `_promote_nested_source` 对含 samples/tests 单头文件库的误判（E195 同源） | 从官方 tarball 重新解压完整树到 .orig/.work，重建 .edit-tracker 基线 |
| 3 | 上游 tests/CMakeLists.txt 要求 cmake_minimum_required 2.8，CMake 4.1.2 报 Compatibility < 3.5 removed | CMake 4.x 移除 <3.5 兼容（E187/E103） | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 强制兼容 |
| 4 | conan-verify G1 报缺 build()/export_sources()/补丁调用 | header-only 模板无 build()，G1 配方完整性要求（E257） | 补 `build()`（apply_conandata_patches）+ `export_sources()`（export_conandata_patches） |
| 5 | G2 test_package 报 "Imported target tinydir::tinydir includes non-existent path .../p/include" | package() 中 copy() 相对 dst="include" 被解析到 build 目录，头文件未进包（DRAFT-boost-te 同源） | copy() dst 改用绝对路径 `os.path.join(self.package_folder, "include")` |
| 6 | finish W3 junk_check 报 JC1/JC5 命中 `archives/c/cloog/0.21.1/.build-closed` 等 2 个跟踪文件 | 新库分支零提交 → junk_check 回退 full 模式（git ls-files 整仓），命中 origin/main 其他库历史遗留跟踪杂项（DRAFT-boost-te 同源） | 基线隔离复验：记录路径+SHA-256（e3b0c442... 空文件）→ `git rm --cached` 临时隔离 → 复跑 W3 通过 → `git reset HEAD`+`git restore` 原样恢复 → 核对恢复后 SHA-256 一致 |

## 源码修改

无补丁（patches/ 为空）。tinydir 为 header-only 单头文件库，无任何源码改动。

## 依赖版本

无第三方依赖（header-only，dirent/stat/unistd 来自 OHOS libc）。

## 验证结果

```bash
# 上游测试（tests/CMakeLists.txt 注册，cbehave 框架）
ctest --output-on-failure   # Test #1 file_open_test: Passed (1/1)
# 鸿蒙专项消费者测试（28 项断言全过）
./test_tinydir_harmonyos    # 结果: 全部通过 (exit 0)
# conan create 完整门禁
conan-verify tinydir 1.2.4  # G1-G4/L2/L4/L5 全过，test_package 消费者测试运行 PASS
# W3 本地 CI 模拟
finish tinydir 1.2.4 built  # setup.sh + build_and_test.sh 通过，.ci-result.json exit_code=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/t/tinydir/1.2.4/conanfile.py | header-only 配方（BSD-2-Clause） |
| archives/t/tinydir/1.2.4/conandata.yml | 官方源 + SHA-256 |
| archives/t/tinydir/1.2.4/test_package/ | 消费者测试（鸿蒙专项，28 断言） |
| archives/t/tinydir/1.2.4/reports/ | conan-verify / W3 报告 |

## 注意事项

- tinydir 1.2.4 迭代目录**不跳过 `.` 与 `..`**：2 个文件的目录迭代出 4 个条目（`.`, `..`, 文件…），`open_sorted` 后 `n_files=4`，`Beta.dat` 在 index 2。消费者需自行过滤 `.`/`..`。
- 上游测试总数：源码声明 2 个独立用例（file_open_test 1 个 SCENARIO + windows_unicode_test 1 个 SCENARIO，MSVC 专属）；OHOS 配置实例化 1 个（file_open_test），实测通过 1/1；windows_unicode_test 仅 `if(MSVC)` 分支构建，OHOS 不实例化。
## 结束

编译结束，最终状态：built（W3 本地 CI 通过，exit_code=0）。

---

## 知识候选台账（knowledge_candidate_ledger）

执行端在本轮适配中收集的全部非噪声候选及查重结果（四范围：正式知识 doc/E*.md、图谱 E*.kv、草稿 drafts/、principles）：

### 候选 1：CMake 4.x 移除 <3.5 兼容（上游 tests/CMakeLists.txt cmake_minimum_required 2.8）
- 真实错误：`Compatibility with CMake < 3.5 has been removed from CMake`
- 根因：CMake 4.x 向后兼容性限制，旧项目最低版本声明过旧
- 修复：`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（不改上游文件）
- 验证：cmake configure 通过 → make → ctest 1/1
- 适用范围：所有 cmake_minimum_required <3.5 的上游项目
- **查重：exact_duplicate（E187 add-cmake-flag，E103 bump-cmake-minimum-version 同覆盖）**；与本轮完全一致，无新增差异 → 复用既有条目

### 候选 2：init-build 嵌套源码提升误判（samples/ 提升为源码根，丢失单头文件与 tests/）
- 真实错误：.work 中只剩 samples 内容，tinydir.h、tests/ 丢失
- 根因：`_promote_nested_source` 对 samples/tests 并存结构误判（与 E195 记录的同函数缺陷同源）
- 修复：从官方 tarball 重新解压完整树
- 验证：26 文件齐全，构建与测试正常
- 适用范围：含 samples+tests 的单头文件库（E195 为 src/ 子目录场景，本候选为其 samples/ 变体）
- **查重：causal_duplicate（E195 restore-from-tarball 根因同一函数）**；E195 记录的同源缺陷已覆盖，无独立新增知识（机制、修复手段均相同）→ 复用既有条目

### 候选 3：header-only 配方 G1 缺 build()/export_sources()
- 真实错误：`conanfile.py 缺少: build() 方法 / export_sources() 方法 / 补丁应用调用`
- 根因：header-only 模板不定义 build()，与 G1 配方完整性门禁冲突
- 修复：补 build()=apply_conandata_patches + export_sources()=export_conandata_patches
- 验证：G1 PASS
- 适用范围：所有 header-only / 无编译配方
- **查重：exact_duplicate（E257 no-op-build-for-header-only 草稿，E321/E322 header-only 配方族）** → 复用既有条目

### 候选 4：header-only package() copy() 相对 dst 陷阱 → 包内无 include
- 真实错误：`Imported target "tinydir::tinydir" includes non-existent path .../p/include`；package() WARN: No files in this package!
- 根因：Conan 2 copy() 相对 dst 解析到 build 目录而非 package 目录
- 修复：dst 用绝对路径 `os.path.join(self.package_folder, "include")`
- 验证：G2 通过，消费者测试运行 PASS
- 适用范围：所有 copy-based 打包配方（header-only / 资源包）
- **查重：exact_duplicate（DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental 草稿已逐字覆盖该陷阱与修复）** → 复用既有草稿

### 候选 5：新库分支零提交时 W3 junk_check 回退 full 模式命中 main 基线噪声
- 真实错误：`JC1: 2 个运行时状态文件被跟踪: archives/c/cloog/0.21.1/.build-closed ...`；JC5 未登记隐藏文件
- 根因：分支零提交 → `git diff origin/main...HEAD` 为空 → junk_check 回退 full 模式（git ls-files 整仓），命中其他库历史遗留跟踪杂项；真实 CI 走 pr.diff 模式不受影响
- 修复：基线隔离复验（记录路径+SHA → `git rm --cached` 临时隔离 → 复跑 W3 → `git reset`+`git restore` 原样恢复 → 核对恢复后 SHA-256）
- 验证：隔离后 W3 JC 通过，恢复后 `git ls-files`/status 干净、SHA-256 前后一致
- 适用范围：共享 build_in_harmonyos 仓库所有新库分支的 finish/W3 流程
- **查重：exact_duplicate（DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental 草稿第二部分已覆盖零提交 full 模式基线噪声及规避）** → 复用既有草稿

### 候选 6：tinydir 迭代包含 `.`/`..`（2 文件目录迭代 4 条目）
- 真实错误：无错误；为库行为观察（迭代含 `.`/`..`，open_sorted 后 n_files 含二者）
- 根因：tinydir 直接包装 dirent，未过滤 `.`/`..`
- 修复：消费者自行过滤；已在鸿蒙专项测试断言真实行为
- 适用范围：tinydir 自身（库行为，非跨库可复用编译知识）
- **查重：非噪声但为库专属行为（L3 笔记），不构成跨库知识** → 记录于本 notes.md，不入知识图谱

## 七轴查重汇总

| 轴 | 候选 | 结论 |
|---|---|---|
| exact_duplicate | 候选 1/3/4/5 | E187、E257、DRAFT-boost-te 逐字覆盖，无独立差异 |
| causal_duplicate | 候选 2 | E195 同根因（_promote_nested_source），机制相同 |
| trigger_overlap | 全部 | 触发工具/门禁与既有条目一致（conan-verify G1/G2、junk_check full 模式） |
| solution_overlap | 全部 | 修复手段与既有条目推荐完全一致（policy 标志、绝对路径 copy、隔离复验） |
| combination_novelty | 无 | 无跨条目组合出新知识的情况 |
| boundary_novelty | 无 | 候选 2 的 samples/ 变体仍属 E195 根因边界内，未产生新反例 |
| test_migration_novelty | 无 | 无测试迁移到新平台的新增知识 |

## 路径决定

- 完整重复且无独立差异 → 复用既有条目（E187/E103、E195、E257、DRAFT-boost-te）
- **决定：`reuse_existing`（走路径 A，不新建草稿）**
- 说明：全部候选均已被既有正式知识/草稿覆盖，无经验证且可跨库复用的新增差异；tinydir 为无坑点单头文件库，无需路径 B 草稿。知识候选台账与七轴查重已在本 notes.md 完整记录。
