# libftp 1.5.0 R04 知识查重判定（executor_local_required）

- task_id: libftp-1.5.0-r04-full-census-and-cmdline-suite-execution-pc1-19-20260927T075911Z
- 快照: /storage/Users/currentUser/.ohpc-knowledge-snap/libftp-1.5.0-r01-bootstrap-and-adapt-pc1-19-20260922T160045Z（main @ 48d9cee6，外置只读稀疏）
- 扫描范围: knowledge/graph/E*.kv(540) + knowledge/doc/E*.md(540) + knowledge/drafts/*.kv + DRAFT-* 配对

## R04 候选
1. 上游测试清点必须覆盖工程全部测试面（不得只扫 test/，遗漏 app/cmdline/test/ 33 宏 → 少报）；
2. cmdline 套件真实执行（33 用例，纯 gtest 无阻塞）；
3. client.cpp 依赖缺口必须实际排查（组件导出扫描 + 头文件可用性 + 最小复现）后给结论，不得未试即断。

## 判定
- 候选 1：**等价命中 E596**（DRAFT，同 tarball 子包 N 清点——父 tarball 全量注册面取最大计数，
  "实测 N > 声明 N 即判少报直接不通过"；rec_approach=parent-tarball-max-counting-surface）。
  本任务全量口径 104（test/ 71 + app/cmdline/test/ 33）正是该方案的应用 → 路径 A 等价命中，不建新草稿。
- 候选 2：E292（layered-ctest-migration：可执行子集真实运行）+ E342（FetchContent 测试框架离线替代）
  继续覆盖 cmdline 套件的独立构建运行技术路径 → 路径 A 等价命中。
- 候选 3：E292 rec_description 已含"缺依赖记录为依赖闭环缺口而不是目标测试失败"，R04 的
  boost::process 组件缺失（全部制品仓配方 process 组件引用=0 + 最小复现 find_package CONFIG 失败）
  为具体库事实（恢复条件已记录于台账），其方法论已被 E292 覆盖，非新增通用知识 → 路径 A。
- R01 路径 B 草稿对 DRAFT-libftp-1.5.0-openssl-flat-cmakedeps-target-rename.{kv,md} 复核有效并随本 PR。

## 草稿成对审计（R01 草稿对，本轮复核）
- kv SHA-256: 346ef5ad3d6baaeb0841799ce33abf9d48e7e770086cbe9742f2a0340032f7a
- md SHA-256: 325402f36879c450a5203f59e477ab0ec77417dc067fc08e577a8db8da9ec06e
- 同 stem 配对存在；kv 12 字段齐全；白名单 knowledge/drafts/DRAFT-libftp-1.5.0-*.md|.kv 匹配。
- R04 无新增草稿（knowledge_decision: reuse_existing，路径 A）。