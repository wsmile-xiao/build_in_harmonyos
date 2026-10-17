# 知识候选台账 — irrtoolset 5.1.3 (Path B 知识库扩展候选)

任务: irrtoolset-5.1.3-r01-pc4-19-20260916T121536Z
日期: 2026-09-16
执行端: pc4-19 / oh-executor + openharmony-compile-agent

## 一、适配过程非噪声候选总览

| # | 候选 | 真实错误证据 | 根因 | 修复 | 验证 | 适用范围 |
|---|------|------------|------|------|------|---------|
| K1 | 官方 tag 归档无 configure | conan create 报 `configure: inaccessible or not found` (Error 127) | GitHub archive tarball 不含 autoreconf 产物 | build() 先 `autoreconf -fi` 自举 + tool_requires automake/1.18 + libtool/2.5.4 | G2 conan create 通过, W3 100% | 任何以 GitHub tag 归档为源的 autotools 库 |
| K2 | HMDFS config.status 临时目录 umask 077 | `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 将 0700 临时目录投影为不可写 drwx--S--- | _drop_umask_077 补丁去掉生成 configure 的 umask 077 | configure 正常生成 Makefile, G2 通过 | 任何 HMDFS 主机的 autotools 库 |
| K3 | 源码相对包含在 out-of-source 构建失败 | `fatal error: 'dataset/Pix.h' file not found` | 源码 `#include "dataset/Pix.h"` 依赖源码树目录结构, 构建树缺同级目录 | layout() 用 basic_layout(src_folder=".") + folders.build="." 改为 in-source 构建 | G2 通过 (adjtimex/argp-standalone 同方案) | 任何源码树内部使用相对包含头文件的 autotools/CMake 库 |
| K4 | make -j>1 在 HMDFS jobserver fifo EPERM | E074 知识 | SELinux 禁用户 FIFO | make -j1 | W3 通过 | 已覆盖 (E074) |

## 二、四范围查重结果

### K1 (autoreconf 自举 + tool_requires)
- 正式知识: E116 (Automake::Config perl 模块)、E175/E178 (autoreconf-regenerate) 部分相关
- 图谱: index.tsv 217 行 E116 相关系目
- 草稿: DRAFT-6051 (automake/1.18 远端包缺 .aclocal-real)、DRAFT-6053 (NEWS missing)
- 配方先例: abiword-plugin-clarisworks、argp-standalone、abiword-plugin-docbook 等 ≥5 个已用同方案
- 结论: **已有完整先例, 无新增差异 → 复用, 不建草稿**

### K2 (HMDFS umask 077)
- 正式知识: E011、E114、E129、E136 全部覆盖同一问题
- 结论: **完全重复 → 复用 (R12 指向 E114/E129)**

### K3 (相对包含 → in-source) ★ 唯一新增候选
- 正式知识: E434 (vpath-build, copystamp 场景不同)、E519 (install-data-am EXTRA_DIST 场景不同) — 均非本场景
- 图谱: index.tsv 无覆盖 "源码相对包含需 in-source 构建" 的条目
- 草稿: DRAFT-audacious-buildsys-in-source-static-chain (自研 buildsys.mk 非 automake 场景, 机制不同)；DRAFT-stdex (header wrapper 遮蔽, 不同)
- 配方先例: adjtimex、argp-standalone、accountsservice、acsccid、apache-arrow、aravis 等 ≥8 个已用 basic_layout(src_folder=".") 但知识库无正式条目沉淀该模式的原因/条件
- 结论: **部分覆盖 (配方有实践, 知识库无正式条目), 存在新增差异 (把"相对包含→in-source"作为可跨库复用决策条件)** → 走 Path B, 建草稿

### K4 (make -j1)
- 正式知识: E074 已覆盖 → 复用

## 三、七轴查重 (K3)

| 轴 | 判定 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无同词条正式条目或草稿 |
| causal_duplicate | 否 | E434/E519 同类不同因 (copystamp/EXTRA_DIST, 非相对包含) |
| trigger_overlap | 部分 | E434/E519 同触发段 (autotools 构建) 但错误签名不同 (找不到头文件 vs copystamp/cannot stat) |
| solution_overlap | 部分 | 与 DRAFT-audacious 同用 in-source layout, 但该草稿针对自研 buildsys.mk (无 VPATH), 本候选覆盖标准 automake VPATH 场景下相对包含问题 |
| combination_novelty | 是 | "源码相对包含头文件 → out-of-source 构建树缺结构 → in-source 布局" 作为独立决策条件未被正式沉淀 |
| boundary_novelty | 是 | 边界明确区分: 相对包含 (需 in-source) vs 仅 -I 引用 (out-of-source 可行) vs 自研无 VPATH 构建系统 |
| test_migration_novelty | 否 | 无测试迁移维度 (被测试问题) |

## 四、路径判断

- K1/K2/K4: **reuse_existing** (已有正式知识/配方先例, 直接复用)
- K3: **new_draft** (已验证可跨库复用, 查重为未命中+部分覆盖, 存在新增差异)
- 路径: **Path B (知识库扩展)** — 与任务类型一致 (【知识库扩展】前缀)
- 草稿将随本库归档文件同一 PR 交付 (知识草稿与三方库归档同 PR 规则)

## 五、附加观察 (非知识候选)

- peval 初始化强制连接 IRR whois 远端 (RADB), 无网络环境下挂起/段错误 — 库自身行为, 非适配知识
- W3 junk_check full 模式误扫其他库基线文件 (cloog .build-closed/.staging-verified) — 已通过 JUNK_PR_DIFF prdiff 隔离解决, 属基线隔离复验流程 (oh-executor 规则), 非本库知识