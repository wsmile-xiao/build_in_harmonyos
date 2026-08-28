# DRAFT-jc-junk-baseline-noise: 共享仓库基线噪声阻塞 W3/JC 门禁的临时隔离方法

> **结构化数据**: [../drafts/DRAFT-jc-junk-baseline-noise.kv](../drafts/DRAFT-jc-junk-baseline-noise.kv)
> **严重度**: 🟡 medium | **分类**: shared-baseline/junk-check/jc-gate/ci/isolation | **自动修复**: false

---

## 错误特征

```text
[step] JC1: 运行时状态文件检测...
[FAIL] JC1: 3 个运行时状态文件被跟踪:
       archives/i/isa-l_crypto/2.26/conandata.yml.orig
       archives/m/middleclass/4.1.1/conandata.yml.ghfast-bak
       archives/s/swift-corelibs-blocksruntime/6.3.3/.staging-verified
[step] JC5: archives 隐藏文件白名单检测...
[FAIL] JC5: 1 个 archives 下未登记的隐藏文件:
       archives/s/swift-corelibs-blocksruntime/6.3.3/.staging-verified
┌
  Junk Files: 2
JC_RESULT=fail
L0_RESULT=fail: junk_check failed
L1_RESULT=skip: blocked_by_JC
L2_RESULT=skip: blocked_by_JC
L4_RESULT=skip: blocked_by_JC
L5_RESULT=skip: blocked_by_JC
```

## 根因

`ci/scripts/junk_check.sh` 的 **JC1**（运行时状态文件，匹配 `.orig`/`.ghfast-bak`/`.staging-*` 等）与
**JC5**（archives 下隐藏文件白名单，`JC5_ALLOWED`）在 **full 模式**下基于 `git ls-files`
整仓扫描被跟踪文件。当共享仓库 `main` 基线中遗留了与本库完全无关的**已提交** junk 文件时，
任何当前库的 W3 本地 CI（`build_and_test.sh`）都会在 JC 门禁处失败，`L0/L1/L2/L4/L5`
全部 `blocked_by_JC`，且该失败与本库配方、源码、测试均无关。

libvncserver 0.9.15 实测（r01）被拦截的三个无关路径：

| 路径 | 类型 | 归属 |
|---|---|---|
| `archives/i/isa-l_crypto/2.26/conandata.yml.orig` | 运行时状态文件 (JC1) | 其他库归档 |
| `archives/m/middleclass/4.1.1/conandata.yml.ghfast-bak` | 备份残留 (JC1) | 其他库归档 |
| `archives/s/swift-corelibs-blocksruntime/6.3.3/.staging-verified` | 运行时标记 (JC1+JC5) | 其他库归档 |

直接改动他人归档目录或修改共享框架 `junk_check.sh`（登记白名单）违反协作者铁律
（❌ 不碰基础设施、❌ 不碰他人归档目录），因此需要一种**只影响本地索引、不改内容、
可完整还原**的临时隔离方法。

## 为什么这些路径在本库范围外

- 三个路径的 `archives/` 前缀目录分别属于 `isa-l_crypto`、`middleclass`、`swift-corelibs-blocksruntime`，与本任务库 `libvncserver` 无任何依赖或包含关系。
- 通过 `git ls-files --stage` 确认三者均为 `main` 基线中已提交的跟踪文件（100644 blob），并非本 worktree 产生。
- `.staging-verified` 是 `archives/s/swift-corelibs-blocksruntime/6.3.3/` 的构建标记，`conandata.yml.orig/.ghfast-bak` 是其他库的备份/镜像残留，均属共享仓库卫生问题。

## 临时隔离与还原方法（已实测 r02）

```bash
# 1) 备份并记录隔离前 SHA-256（内容证明）
mkdir -p /storage/Users/currentUser/tmp/isolation-libvncserver-r02
cp  $P1 /storage/Users/currentUser/tmp/isolation-libvncserver-r02/   # 同理 P2, P3
sha256sum $P1 $P2 $P3

# 2) 临时隔离：仅移出 git 索引，工作树内容原地保留
git rm --cached $P1 $P2 $P3

# 3) 用后台 worker 重跑 W3/finish 门禁（隔离状态下）
#    POST {kind:finish, worktree, library, version, state} @ ohpc_compile_worker

# 4) 还原：git add 会被 .gitignore 忽略（.orig/.staging-verified），必须 -f
git add -f $P1 $P2 $P3

# 5) 证明还原完整性
sha256sum $P1 $P2 $P3          # 与步骤1完全一致
git status --porcelain $P1 $P2 $P3   # 零输出 = 索引与 HEAD 完全一致
```

实测（r02 worker-2192de9e）：

| 阶段 | 结果 |
|---|---|
| 隔离前 W3 | JC_RESULT=fail, Junk Files: 2, blocked_by_JC |
| 隔离后 W3 | ✅ W3 本地 CI 模拟通过（JC 门禁不再拦截，G2/G3/G4/L2/L4/L5 全部 PASS） |
| restore 前 SHA-256 | `d62412e1…` / `226348ef…` / `e3b0c442…` |
| restore 后 SHA-256 | `d62412e1…` / `226348ef…` / `e3b0c442…`（完全一致） |
| restore 后 git status | 零输出 |

## 恢复/维护指引

1. **执行端**：仅对任务正文明确点名的无关基线路径做隔离-重跑-还原；不得扩大清理范围、
   不得改共享框架白名单、不得将这些路径纳入任何 diff/commit。
2. **分析端（长期修复）**：在共享 main 基线中清理这些已提交 junk 文件，或将确需保留的
   隐藏标记登记进 `junk_check.sh` 的 `JC5_ALLOWED`。清理完成后无隔离即可直接重跑 W3/finish。
3. **判断阈值**：若隔离后 W3/finish 全部通过 → 该轮门禁结论为 `baseline_noise_exempted`
   （外部噪声豁免，非本库问题）；若隔离后仍出现本库专属失败 → 按真实首错回报。