# 知识候选台账 — flatbush 1.5.0（task: flatbush-1.5.0-r01-pc7-13）

执行端：pc7-13；worktree: /storage/Users/currentUser/pd/worktrees/flatbush-1.5.0
分支：feat/flatbush-1.5.0；HEAD: 48d9cee6844d0fca1f25e86c2df1293b904855d8（本轮适配前基线）

## 候选 1（非噪声，核心候选）：header-only INTERFACE 库 C++ 标准门控宏须经 cpp_info.defines 传播

- 真实错误：C++17（OHOS profile cppstd=17）消费方编译已安装 flatbush.h 报
  `no template named 'span'`（15 errors），详见 reports/ohos-test-run.log 首段。
- 根因：flatbush.h 用 `#ifndef FLATBUSH_SPAN` 门控 std::span（需 C++20）vs 自带
  span（C++11/17 可用）；上游 CMake `WITH_SPAN=ON` 把 FLATBUSH_SPAN 挂在
  INTERFACE target 上，但 Conan 打包后宏不进包，配方未声明 cpp_info.defines。
- 修复：`self.cpp_info.defines = ["FLATBUSH_SPAN"]`（与上游默认 WITH_SPAN=ON 一致）。
- 验证：鸿蒙专项测试（C++17 + 宏）exit 0；conan create G2 PASS；test_package L1 PASS。
- 适用范围：所有 header-only/INTERFACE 库用编译宏门控 C++ 标准特性、目标 profile
  cppstd 低于宏关闭分支要求标准的场景；可跨库复用。
- 四范围查重：正式知识（E321/E322/E257/E293 相邻）→ 未命中核心差异；
  图谱 index.tsv → 无同签名条目；草稿 knowledge/drafts/ → 无同场景草稿；
  doc/ → E321/E322 仅覆盖 Conan 1→2 迁移与 cmake_file/target_name 设置，
  未覆盖 defines 传播标准门控宏。
- 七轴：exact=false, causal=false, trigger=partial, solution=partial,
  combination_novelty=true, boundary_novelty=true, test_migration=false。
- 关系：similar_to=[E321,E322,E257,E293]；caused_by/prerequisite_of/conflicts_with=[]。
- 结论：**new_draft（路径 B）** — 已验证、可跨库复用、查重未命中/部分覆盖且有新增差异。
  草稿：knowledge/drafts/DRAFT-flatbush-1.5.0-header-only-cxx-standard-macro-cpp-info-defines.kv/.md（同 stem）。

## 候选 2（噪声/流程项，复用既有知识）：W3 junk_check full 模式命中其他库基线文件

- 现象：W3 本地 CI 模拟（junk_check full 模式）命中 origin/main 中其他库已提交的
  跟踪空文件：archives/c/cloog/0.21.1/.build-closed、.staging-verified、
  archives/k/kics/2.1.20/.staging-verified（均 e3b0c44…空 blob，非本库 diff）。
- 处理：基线隔离复验（记录 pre/post SHA-256 一致、临时 git rm --cached 隔离、
  复跑 W3 全绿、原样恢复）；完整审计见 notes.md「基线隔离审计」。
- 查重：与既有草稿 DRAFT-dr_mp3-0.7.2-baseline-noise-isolation、
  DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation、
  DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental 同源
  （causal_duplicate/trigger_overlap=true）。
- 结论：**reuse_existing**，不建新草稿。

## 路径决定

- task_type=知识库扩展（路径 B 候选）；候选 1 满足"已验证、可跨库复用、查重部分覆盖
  且存在新增差异"→ 必须走 **路径 B**，已建立同 stem 的 .md/.kv 草稿并随本库 PR 交付。
- 候选 2 复用既有知识（路径 A 行为），不另立草稿。
- 完整重复/无独立差异 → 不适用（无 exact_duplicate 候选）。
