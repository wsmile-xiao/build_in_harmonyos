# libutf8proc 2.10.0 — Bootstrap 记录

## 任务身份
- task_id: `libutf8proc-2.10.0-r01-bootstrap-and-adapt-pc3-22-20260827T160401Z`
- executor: pc3-22
- 执行 worktree: `/storage/Users/currentUser/junshi_liu/worktrees/pc3-22-libutf8proc-2.10.0`
- 分支: `feat/libutf8proc-2.10.0`
- HEAD: `bb2101fde620632e4c703d36f0bc204007708940`（基于 origin/main 最新 `bb2101fde6`）

## 官方来源核验（bootstrap 证据）
- 官方仓库: `https://github.com/JuliaStrings/utf8proc`
- 标签: `v2.10.0` → commit `a1b99daa2a3393884220264c927a48ba1251a9c6`（GitHub API tags 核验）
- 源码 tarball: `https://github.com/JuliaStrings/utf8proc/archive/refs/tags/v2.10.0.tar.gz`（codeload 官方直链）
- SHA-256: `6f4f1b639daa6dca9f80bc5db1233e9cbaa31a67790887106160b33ef743f136`
- 内容一致性: 本地解包 5 个关键文件（utf8proc.c / utf8proc.h / CMakeLists.txt / README.md / NEWS.md）的 git blob hash
  与 GitHub API git/trees/a1b99daa…?recursive=1 返回的 tree 完全一致 → tarball 与标签 commit 逐字节匹配。
- 许可: MIT（LICENSE.md 明文）

## 构建系统
- 上游同时提供 Makefile 与 CMakeLists.txt；本配方选择 Makefile（`all` 产 `libutf8proc.a` + `libutf8proc.so`）。
- 无外部依赖，纯 C 库，依赖列表为空。

## 骨架清单（本阶段创建）
- `manifest.yaml` — ARCHIVE-SPEC v2.0 版本级 manifest，status=failed（未编译，待 W3 更新）
- `conandata.yml` — sources URL + sha256
- `conanfile.py` — 最小配方（Makefile 构建，静态库）
- `test_package/{conanfile.py, CMakeLists.txt, test.c, MANIFEST.yml}` — L1 测试骨架
- `notes.md` — 本文件

## 阶段结论
- Bootstrap 完成，来源核验通过（source_provenance 确认，非 unavailable）。
- 可进入首轮 Adapt 与本地验证（同一 task_id 统一阶段）。
---

**编译结束**: 2026-08-28 00:33
**最终状态**: built
