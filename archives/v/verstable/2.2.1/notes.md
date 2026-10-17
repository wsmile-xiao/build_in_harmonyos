# verstable 2.2.1 适配笔记

## 编译环境
- 构建系统: 无（header-only 单头文件库，verstable.h 2069 行）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18, aarch64-linux-ohos）
- 状态: built

## 编译步骤

header-only 库无 configure/cmake/make。适配验证方式：
1. 上游测试编译运行：
   - `clang -std=c11 -O2 -I. tests/unit_tests.c -o unit_tests` → exit 0
   - `clang++ -std=c++17 -O2 -I. tests/tests_against_stl.cpp -o tests_against_stl` → exit 0
2. 配方验证：`ohc-run.py conan-verify verstable 2.2.1`（8 道门禁全过）
3. 鸿蒙专项：`clang -std=c11 -O2 -I<src> tests/ohos_smoke.c` → 运行 PASS
4. finish W3：`ohc-run.py finish verstable 2.2.1 built`（W3 exit_code=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误判 mixed → env_unsupported | 单头文件库主体 .h 被 _source_stats 视为中立不计数，只剩 .c/.cpp 测试各 1 → 50% mixed | 按 R47「c↔cpp 兼容族不迁移」人工复核继续适配；沉淀草稿 DRAFT-verstable-2.2.1-langpreflight-single-header-mixed |
| 2 | conan-verify G1 FAIL（缺 build()/export_sources/补丁调用） | header-only 配方省略 build() | 补 no-op build() + export_sources + apply_conandata_patches（E257 既有知识） |
| 3 | G2: "Package type is 'library', but no 'shared' option declared" | header-only 配方漏 shared option | 补 options={"shared":[True,False]}（E283 既有知识） |
| 4 | 包内 include 为空 → test_package CMake 报 include 不存在 | copy() 相对 dst 基准歧义 | 改用绝对路径 os.path.join(self.package_folder,"include") |
| 5 | W3 JC full 模式命中其他库基线垃圾（cloog .build-closed/.staging-verified）阻塞 | 分支无 commit 时 JC 回退 full 模式全仓扫描；origin/main 既有 cloog 适配提交遗留基线文件 | 基线隔离复验（reports/baseline-isolation-audit.json），生成 pr.diff 进入 prdiff 模式完成 W3 |
| 6 | W3 predl 预下载 NotADirectoryError | conandata.yml 注释裸仓库 URL 被预下载正则误提取并子串污染真实 tarball URL | 注释去掉裸 URL（既有 DRAFT-jwt-cpp 等知识，reuse） |

## 源码修改

无补丁（patches/ 空）。上游源码零修改。

## 依赖版本

无外部依赖（W0 检查通过：verstable 无 requires）。

## 验证结果

```bash
# 上游测试（2/2 程序、40/40 用例）
clang -std=c11 -O2 -I. tests/unit_tests.c && ./unit_tests          # exit 0: All done
clang++ -std=c++17 -O2 -I. tests/tests_against_stl.cpp && ./tests_against_stl  # exit 0: All done
# 鸿蒙专项
clang -std=c11 -O2 -I<src> tests/ohos_smoke.c && ./ohos_smoke     # exit 0: OHOS smoke test: PASS
# 配方与 CI 模拟
ohc-run.py conan-verify verstable 2.2.1    # 8 门禁全过
ohc-run.py finish verstable 2.2.1 built    # W3 exit_code=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only Conan 配方（package_type=library + shared option，copy 绝对路径） |
| conandata.yml | 官方源 URL + SHA-256（893981984622f9be8a5a38ca731c5a46f4909af0a06969981b51cc4f506237d9） |
| test_package/ | 消费者测试（test.c 真实调用公开 API）+ MANIFEST.yml 上游声明 |
| tests/ohos_smoke.c | 鸿蒙专项测试用例 |
| test-report.md | 双口径测试台账（40/40 全量 + 2/2 可执行） |
| reports/knowledge-candidate-ledger.md | 知识候选台账 + 七轴查重 + 路径判定 |

## 注意事项

- 知识路径判定: 路径 B（new_draft: DRAFT-verstable-2.2.1-langpreflight-single-header-mixed .md/.kv 对）；
  其余 4 项候选全部命中既有条目/草稿 → reuse_existing
- 非 CLI 库，不创建 commands.json（R38 仅 tool 类型需要）

---

**编译结束**: 2026-09-19 02:10
**最终状态**: built (COMPLETED)
