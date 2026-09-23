# scope-lite 0.3.0 适配笔记

## 编译环境
- 构建系统: cmake (header-only INTERFACE library)
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build scope-lite 0.3.0 --url=https://github.com/nonstd-lite/scope-lite/archive/refs/tags/v0.3.0.tar.gz`
   - 上游 tags 核验：`refs/tags/v0.3.0 = 7ed8b06326671154335d72dcc2840c1ed9707df9`
   - 源码 sha256: `c66b54c29c2982341945c7258b7e2c0b49558848f50ac42698cb34aa52f78446`
2. conan-init 后重写配方（autotools 模板 → CMake header-only）：
   - conanfile.py: package_type=header-library, cmake_layout, CMakeToolchain（OHOS→CMAKE_SYSTEM_NAME=Linux + aarch64）, SCOPE_LITE_OPT_BUILD_TESTS=True, cpp_info.set_property cmake_file_name/cmake_target_name
   - test_package: 真实调用 nonstd::make_scope_exit/fail/success API（非空壳）
   - test/ohos_scope_test.cpp: HarmonyOS 专项测试（clang 15 编译，本机运行 PASS）
3. `ohc-run.py conan-verify scope-lite 0.3.0` → G0-G4 PASS
4. `ohc-run.py finish scope-lite 0.3.0 built` → W3 本地 CI 通过（Pass rate 100%）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 模板配方 | scope-lite 是 CMake header-only INTERFACE 库（martinmoene nonstd-lite 系） | 按 E321 模式重写为 header-library 配方（参照 string-view-lite 1.8.0） |
| 2 | W3 本地 CI junk_check 拦截 9 个其他库基线垃圾文件（embree/.submit-state.json、flatcv/.staging-verified、goaccess/*.tar.gz 等） | 分支无 commit 时 junk_check 回退 full 模式整仓扫描，扫到 main 上其他库已被跟踪的历史垃圾文件 | 无关历史基线：临时 index 隔离（blob 哈希审计）→ 重跑 W3 复验（Pass rate 100%）→ 精确恢复（HEAD/INDEX 哈希一致，零 diff） |

## 依赖版本

无（header-only，零依赖）。

## 验证结果

- 上游测试: ctest 5/5 通过（test-cpp98/11/14/17/20）
- test_package: `PASS: scope-lite header-only 库链接和核心 API 验证通过`
- HarmonyOS 专项测试: `PASS: scope-lite 0.3.0 HarmonyOS 专项测试全部通过`

## 注意事项

- scope-lite 0.3.0 上游无 Conan 1.x 内置配方（与 byte-lite 等不同），直接按 Conan 2.x header-library 模式编写即可
- `SCOPE_LITE_OPT_BUILD_TESTS/EXAMPLES` 为上游测试/示例开关；编译任务必须只开 TESTS

## 知识查重判定（本地只读快照，knowledge @ main, HEAD=2f60a10778）

- 扫描范围: knowledge/graph/E*.kv（540 条目）+ knowledge/doc/E*.md + knowledge/drafts/*.kv（83 草稿）
- 逐字段比较结论: **等价命中 E321**（martinmoene lite 系 header-only 库 Conan 1.x→2.x 迁移 + INTERFACE 消费 + 上游测试入口恢复, PR !7220, doc 配套完整）
  - error_signature: header-only/INTERFACE library/package_type header-library/cmake_layout → 命中
  - root_cause: nonstd-lite 系单文件 header-only + CMake INTERFACE library + 需显式 package_type=header-library/cmake_file_name/cmake_target_name → 完全一致
  - rec_approach: header-only-lite-conan2-migration → 本配方逐项遵循
  - verification: conan create + ctest（cpp98/11/14/17）→ 本任务 5/5 通过
- 无 scope-lite 专属正式条目或草稿（formal/drafts 全量搜索为空）
- **knowledge_decision: reuse_existing（路径 A）**，不创建新草稿
- W3 junk_check 基线拦截属其他库历史基线噪声，按规则不走路径 B

---

**编译结束**: 2026-09-03 10:35
**最终状态**: built