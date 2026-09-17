# 原子性审计 — tar 1.35（R02 任务 9）

**task**: tar-1.35-r02-pc3-13-20260913T113300Z
**时间**: 2026-09-13

## 1. R01 commit 6dfca76ef5 处置决定

- **决定**: 保留（不回退、不重建、不推送）
- **证据**:
  - commit 内容逐文件核对：33 文件，**0 个越界**（全部在 `archives/t/tar/` 范围内）
  - 未 push、未创建 PR（无远端交付行为）
  - R02 在相同分支继续追加台账/草稿/实测证据，保留 commit 保持历史连续性
- **硬门禁合规**: R01 创建本地 commit 未 push 属既定事实（已记录 r01-commit-disposition.md）；R02 起严格遵守硬门禁规则 4——未满足门禁时禁止 push/PR/rebuild

## 2. 本库 diff/staged/commit/PR 文件列表单库范围核对

- R01 commit（6dfca76ef5）：文件清单 33 项全部 `archives/t/tar/`（0 越界）
- R02 新增（工作树待提交）：`knowledge/drafts/DRAFT-tar-1.35-*.kv|.md`（3 组 × 2）+ `archives/t/tar/1.35/reports/*r02*`（台账/审计/实测证据）——知识草稿与三方库归档同 PR（路径 B 规则），无其他库目录
- **排除项**: `archives/l/libXext/`（会话开始前已存在的无关修改，未 touch）；`.build-cache/`（W3 运行时缓存，已删除）；`test_package/` 运行时残留（已清理，仅保留 MANIFEST.yml/conanfile.py/ohos_specific_test.sh/test_tar.sh）

## 3. commands.json 声明（R38/L0k）

- 文件: `archives/t/tar/commands.json` → `{name=tar, type=tool, versions={"1.35":{"ref":"tar/1.35","binary":true}}}`
- 已暂存、进入 commit（`git cat-file -e HEAD:archives/t/tar/commands.json` OK）、出现在 `origin/main...HEAD` 文件清单
- R38/L0k 复跑: W3 日志 `[ok] commands.json valid (type=tool)`

## 4. 其他库基线 .ci-trigger 处置

- 路径: `archives/u/util-linux-login/2.42.2/.ci-trigger`（util-linux-login 既有基线，空文件）
- 隔离前 SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- 处置: R01 曾临时隔离（mv + `git rm --cached`）使 W3 JC 门禁通过后**原样恢复**；R02 核验仍为 `e3b0c442...`，`git status` 无改动，**未进入本库 diff/PR/知识库**

## 5. W2/W3 基线恢复证据

- R01 W3 本地 CI 通过后 `.ci-result.json`（exit_code=0，integrity_hash 4b60c362bf3c0309）仍保留
- R02 门禁复验将在任务 10 执行（conan create/test_package/W2/W3 真实输出）

## 结论

原子性通过（P0/P1 清零）：单库范围、commands.json 声明完整、基线文件未污染、运行时残留已清理。PR 文件列表仅含 archives/t/tar/ 与同 stem 知识草稿。