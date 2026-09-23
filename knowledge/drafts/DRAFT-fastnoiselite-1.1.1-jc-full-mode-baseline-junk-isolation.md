# DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation：W3/JC 全仓 full 模式命中其他库基线垃圾文件——git rm --cached 隔离 + restore 恢复

> Contributor: pc4-7 | Status: Draft | Updated: 2026-09-19
> Source: fastnoiselite 1.1.1 适配（Path B 知识库扩展）；触发场景：`finish` W3 本地 CI 模拟 JC 拦截
> 对应：`knowledge/drafts/DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation.kv`

## 现象

`ohc-run.py finish <lib> <ver> published` 的 W3 本地 CI 模拟失败：

```text
❌ build_and_test.sh 失败 (RC=1)
  Junk Files: 2
  JC_RESULT=fail
  [fail] JC1: 3 个运行时状态文件被跟踪:
         archives/c/cloog/0.21.1/.build-closed
         archives/c/cloog/0.21.1/.staging-verified
         archives/k/kics/2.1.20/.staging-verified
  [fail] JC5: 3 个 archives 下未登记的隐藏文件: ...
  blocked_by_JC → L0/L1/L2/L4/L5 全 skip
```

**关键点**：这些文件不是当前库的，而是其他库（cloog、kics）已合入
origin/main 的空标记文件（git blob = `e69de29b…`，空 blob；SHA-256 =
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`）。

## 根因

`ci/scripts/junk_check.sh` 在本地开发分支无 PR diff 时回退 **full 模式**，
用 `git ls-files`（**索引跟踪状态**）全仓扫描（日志：`检查模式: full (77768 个文件)`）。
其他库基线中已跟踪的空 `.build-closed`/`.staging-verified` 被全仓命中。

**陷阱**：JC 读的是 git 索引（ls-files），不是工作区文件——第一反应"把工作区文件
mv 走"是无效的，文件仍在索引中，JC 照样命中。必须从**索引**层面隔离。

## 修复（已验证）

基线隔离复验四步（不可修改/提交/写入 PR 这些文件）：

```bash
# 1) 记录隔离前 SHA-256
sha256sum archives/c/cloog/0.21.1/.build-closed \
         archives/c/cloog/0.21.1/.staging-verified \
         archives/k/kics/2.1.20/.staging-verified
#    → e3b0c442…（空文件，三处相同）

# 2) 临时取消跟踪（文件保留工作区，从索引移除）
git rm --cached archives/c/cloog/0.21.1/.build-closed \
                archives/c/cloog/0.21.1/.staging-verified \
                archives/k/kics/2.1.20/.staging-verified

# 3) 复跑受影响门禁
python3 scripts/ohc-run.py finish fastnoiselite 1.1.1 published   # W3 PASS

# 4) 原样恢复 + 核对
git restore --staged archives/c/cloog/0.21.1/.build-closed \
                    archives/c/cloog/0.21.1/.staging-verified \
                    archives/k/kics/2.1.20/.staging-verified
sha256sum ...          # 恢复后仍为 e3b0c442…，与隔离前一致
git ls-files -s ...    # 100644 e69de29b…（= 基线空 blob）
git status --porcelain | grep -E 'cloog|kics'   # 无输出 = 无该路径变更
```

复验结论：隔离前 SHA-256 == 隔离后 SHA-256（均为 e3b0c442…），当前库
diff/staged/PR 不含这些路径，W3 build_and_test.sh 通过。

## 适用范围

任何仓库 main 基线已含其他库运行时标记文件、本地 W3 走 full 模式全仓扫描的场景。

## 边界 / 反例

- 只有确认文件属于"提交前已存在、其他库、空标记/运行状态标记"时才走隔离；
  若文件属于当前库，必须在当前库内删除/处理，不得隔离绕过
- 隔离后必须原样恢复（restore --staged），禁止把隔离状态带进 commit
- 禁止 `git add -A`（会把隔离状态或无关文件带进 commit）

## 关系

- similar_to: E256（staging-verified 相关，binary patch 场景，不同）
- 适用原则: W3（本地编译验证）、W2（PR 原子性）
