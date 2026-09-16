# DRAFT-makedepend-1.0.10-finish-prereq-deprecated-markers — finish Step10 就绪预检索要 v3.0 已废弃标记，照做会自招 JC 拦截

> **Contributor**: OpenDesk (K4T9) | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: medium | **Category**: framework / archive-spec / finish
> **Audience**: 所有走 `finish` → `submit` 的新库适配者

## 问题（Symptom）

`finish` 的 Step 10「submit 就绪预检」报告 3 项未就绪，其中 2 项是**规范里已废弃**的产物：

```text
ℹ️ Step 10/10: submit 就绪预检...
ℹ️   ❌ test-report.md — 需创建 reports/test-report.md
ℹ️   ❌ packaging/ — 需创建 packaging/ 目录并打包
ℹ️   ❌ .staging-verified — 需创建 .staging-verified 空文件
ℹ️   ✅ build-closed marker
⚠️   ⚠️ 3 项未就绪，submit 前需修复
```

同一轮 `finish` 的 Step 6 也报同类缺口：`目录缺失: packaging` / `缺少 release tar.gz` / `缺少 debug tar.gz`。

## 根因（Root Cause）

1. `knowledge/ARCHIVE-SPEC.md` v3.0（2026-06-22 生效）已明确：
   - `packaging/` → **废弃**（"Conan 体系替代手动 tar.gz 打包"）
   - `.staging-verified` → **废弃**（"Conan 自带隔离验证"）
   并把二者列入"废弃文件处置表"。
2. 但 `finish` 的就绪预检仍按 v2.0 时代的交付物清单检查，未随 v3.0 同步。
3. **更关键：照做会被门禁拦死。** `.staging-verified` 不在 `ci/scripts/junk_check.sh`
   的 `JC5_ALLOWED` 白名单里，创建它会让 JC1（运行时状态文件）与 JC5（archives 未登记隐藏文件）
   双双失败 —— 全仓唯一存在的 `.staging-verified`（`archives/c/cloog/0.21.1/`）
   正是当前 main 上被 JC 拦截的那两个脏文件之一。
   于是形成死循环：**预检要求创建 → 创建后 JC 拦截 → W3/finish 阻塞**。

## 仓内先例证据（2026-09-12 实测统计）

| 产物 | 全仓计数 | 近期提交情况 | 结论 |
|---|---|---|---|
| `packaging/` | 55 / 5257 个包（均为老包） | 最近 10 次合并提交 **0 个**带它 | 不创建 |
| `.staging-verified` | **1 / 5257**（cloog 0.21.1，JC 拦截对象） | 0 | **绝不创建** |
| `reports/test-report.md` | 282 / 5257 个包 | 最近 10 次提交 0 个新增（唯一相关是删除） | 可选，可跳过 |

## 查重差异（为何新增）

| 既有条目 | 主题 | 差异 |
|---|---|---|
| ARCHIVE-SPEC v3.0（文档） | 定义 `packaging/` 与 `.staging-verified` 为**废弃** | 只定义"废弃"，未记录"finish 预检仍索要 + 照做被 JC 拦"这一冲突事实 |
| DRAFT-jc-full-scan-baseline-noise-exemption 等 JC 系列 | JC full 模式扫到**他人库**基线垃圾导致阻塞 | 讲扫描范围与索引隔离；本条目讲**当前库自己创建废弃标记**导致的阻塞，根因与对策不同 |
| DRAFT-semver-0.3.0-index-only-baseline-finish-recovery | index-only 隔离恢复流程 | 同上，不同主题 |

结论：知识库无"finish 预检要求 vs v3.0 废弃约定冲突、且照做自招 JC"的条目。

## 方案（Recovery）

**判定这三项为"可跳过"，不创建废弃产物**，其余 finish 步骤结果照常采纳：

```bash
# 只读确认（不改任何文件）：三项是否仍被 finish 索要、是否属废弃清单
grep -nE "废弃" knowledge/ARCHIVE-SPEC.md | sed -n '1,6p'
grep -n "JC5_ALLOWED" ci/scripts/junk_check.sh        # 确认 .staging-verified 不在白名单
git ls-files 'archives/*/*/packaging/*' | wc -l        # 55：老包残留
git ls-files | grep -c '\.staging-verified$'           # 1：仅 cloog（JC 拦截对象）
```

随后以 `submit` 的实际行为为准：W4 审计 + PF1-PF9 硬闸才是建 PR 的真正判据，
finish 的 Step10 属**提示性预检**（警告级别，非 HANDOFF 阻塞项）。

## 禁止事项（forbid）

- ❌ 为"消除警告"而创建 `packaging/`、`.staging-verified`（后者会直接被 JC1/JC5 拦，等于给自己制造 HANDOFF）
- ❌ 把这三项缺口当作本库缺陷去改 `ci/` / `scripts/` 的预检逻辑（框架文件，须单独 PR）
- ❌ 手工打包 tar.gz 塞进 `packaging/`（R19：禁止手动打包，用 `conan create` + `conan upload`）
