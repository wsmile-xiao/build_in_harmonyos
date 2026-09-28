# DRAFT: 数据驱动测试套件的 N 计数口径——rule4 少报高频防线

## 问题场景

GLib 系（GNOME/gtk 生态）数据驱动测试框架的 N（上游测试用例数）申报，
是 rule4 审查最高频的打回点。2026-09 批次连续三件栽坑：

| PR | 库 | 声明 N | 实测 N | 漏算源 |
|---|---|---|---|---|
| #11382 | khelpcenter | 1 | 2 | doc/glossary 的 perl 测试（add_test NAME glossary-checkxrefs） |
| — | pimcommon | 程序级 | 数据级 | 数据驱动用例未计 |
| #12331 | lasem-render | 1187 | 1346 | tests/data/**/*.{svg,mml} 逐文件 g_test_add_data_func 注册 |

## 根因

数据驱动框架的用例注册分两层：

1. **静态注册**：`g_test_add_func` / CMake `add_test`——程序/函数级，肉眼可见
2. **动态注册**：suite 类程序在 main() 里枚举数据目录逐文件注册——
   ```c
   filename_regex = g_regex_new("\\.(svg|mml)$", 0, 0, NULL);
   files = build_file_list(SUITE_DATA_DIRECTORY, filename_regex);  // 递归 + ignore- 前缀排除
   g_slist_foreach(files, add_render_tests, NULL);  // 每文件一个 g_test_add_data_func
   ```
   数据文件数百到千级——按 TEST_PROGS（4 个测试程序）或静态 add_func（13 个）
   申报 N 必然少报。

## 清点法（四步）

1. **静态**：`grep -c "g_test_add_func\|add_test"` 全源码（含 doc/ 等非 tests 目录——
   khelpcenter 的教训：perl 测试在 doc/glossability 下）
2. **动态**：定位数据驱动入口（`g_test_add_data_func` / foreach 数据目录 / 参数化），
   `find tests/data -name "*.svg" ! -name "ignore-*"` 按枚举代码的排除逻辑数全集
   （排除逻辑以代码为准：`strstr(entry, "ignore-") != entry` 前缀排除+目录排除）
3. **N = 静态 + 动态**，正文写明构成（`1346 = 13 单元 + 1333 渲染回归`）供复核加法
4. **豁免逐项定性**（不折叠不减 N）：跑不了的写技术原因（上游 suite.ini ignore 机制/
   环境依赖），豁免数与配置条目对账

## 审查员口径对齐

审核员（CodexBai/Septest）按**上游注册全集**实测——含动态注册。声明 N ≥ 实测 N
是硬线；口径构成透明（加法可复核）能显著降低来回。

## 验证

lasem #12331：修正后 1334/1340（99.5%，6 豁免走上游 suite.ini ignore 机制），
CodexBai 复核通过口径。

---
*来源 PR：#12331（2404_87638649，2026-09-25；khelpcenter #11382 同族案例）*
