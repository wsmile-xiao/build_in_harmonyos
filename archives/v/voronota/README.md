# voronota

Voronota 是分析生物大分子（蛋白质、RNA）三维结构的软件工具，基于原子球的
Voronoi 图：求原子球四元组定义的空切球（Voronoi 顶点），进而构建原子间接触
表面与溶剂可及表面，提供接触查询、接触比较、VoroMQA 模型质量评估等能力。

- 上游：https://github.com/kliment-olechnovic/voronota
- 版本：1.29.4781（2026-04-16 发布）
- 构建：CMake，C++11（核心）/ C++14（JS/LT 扩展），零外部依赖
- 产物：`voronota`、`voronota-js`、`voronota-lt` 三个可执行文件 + 配套分析脚本
  （voronota-contacts、voronota-voromqa、voronota-cadscore 等）

## OHOS 适配说明

- 构建核心 + JS + LT 扩展（`-DEXPANSION_JS=ON -DEXPANSION_LT=ON`，与上游
  quick install 指南一致）；GL 可视化扩展（需 OpenGL）默认关闭。
- 上游测试为 `tests/jobs_scripts/*.bash` 作业脚本流水线（26 个核心脚本），
  需 git checkout 全量 fixtures 与 `tests/jobs_output/` 参考输出做 git-diff
  比对；官方发布包（`voronota_1.29.4781.tar.gz`）内无 `tests/` 目录，故配方在
  `build()` 中运行等价核心流水线（help → 取球 → 算顶点 → 算接触 + JS/LT
  烟雾测试）并做输出非空断言，计数以作业脚本为口径如实上报。
