# ═══ Draft knowledge entry — lang-preflight 对官方发布包自带 doxygen HTML 文档 .js 的 mixed 误判 ═══
# Timestamp: 2026-09-16
# Software: lwip 2.2.1 (task lwip-2.2.1-r01-pc1-16)
# Gate: lang-preflight (R47)
# Status: DRAFT — 同 stem 配对 knowledge/drafts/DRAFT-lwip-2.2.1-lang-preflight-doxygen-js-misdetect.kv

id: DRAFT-lwip-2.2.1-lang-preflight-doxygen-js-misdetect
severity: 3
category: preflight, language, build-system, tooling, docs
trigger_tool: ohc-run|lang-preflight|lang_detect
phase: preflight|language-detection

keywords: lang-preflight, lang_detect, doxygen, doc/doxygen/output/html, mixed,
  misdetect, nodejs, 文档目录, 官方发布包, R47

error_signature: lang-preflight.*detected_language.*mixed|nodejs.*doc/doxygen|620.*\.js|
                  env_unsupported.*mixed.*cmake|source_stats.*nodejs
match_keywords: lang-preflight, lang_detect, doxygen, doc/doxygen/output/html, mixed,
                 misdetect, nodejs, 文档目录, 官方发布包

root_cause: lang_detect.py 的 _SKIP_DIRS 不含 doc，_source_stats 把官方发布包自带
  doc/doxygen/output/html/ 下的 .js（Doxygen 生成的 API 文档脚本）计入 nodejs 主体统计；
  620/823=75% ≥70% 冲突规则触发 → detected=mixed → R47 exit 2 自动写 env_unsupported 终态。
  与既有 DRAFT-emio（辅助 Cargo.toml 被 manifest 扫描命中）同属 lang-preflight 统计污染，
  但触发源不同：本条是源码统计目录未排除 doxygen 文档输出。

affected_scope: 官方发布 zip/tarball 自带 doc/doxygen/output/html（预生成 API 文档）的 C/C++ 库；
  如 lwip 官方 zip 含 doc/doxygen 目录（620 个 html .js）；所有走 ohc-run.py lang-preflight 的适配任务

approach: 复核①顶层 manifest（CMakeLists.txt project(lwIP) → c/cpp 族）；②排除 doc/ 与 contrib 工具后源码统计
  （201 .c + 274 .h + 0 .js → 纯 C）；判定 C/cpp 兼容族后按 R47 继续适配，不被工具 mixed 终态截停；
  若工具已写 env_unsupported 终态，用 result 命令 --force --draft-milestone lang_checked 覆盖

verification_cmd: find <src>/doc/doxygen/output/html -name '*.js' | wc -l
rec_priority: 1
rec_approach: exclude-doc-dir-and-manifest-first
rec_auto_fix: false