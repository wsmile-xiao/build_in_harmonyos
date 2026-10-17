# DRAFT-libjpeg-turbo-3.0.4-jc-full-scan-prdiff-scoping — JC 全仓扫描基线噪声的 prdiff 作用域方案

> **Contributor**: pc2-3 | **Status**: DRAFT | **Updated**: 2026-09-05
> **Severity**: high | **Category**: ohos / ci / infrastructure
> **Audience**: 在共享 build_in_harmonyos 仓库执行 W3/finish、分支零提交/三点 diff 为空的新库执行端

## 问题签名

```text
[FAIL] JC1: 1 个运行时状态文件被跟踪:  archives/f/flatcv/0.3.0/.staging-verified
[FAIL] JC3: 1 个 tarball/打包产物被跟踪:  archives/g/goaccess/1.10.2/ncurses-headers.tar.gz
[FAIL] JC5: 6 个 archives 下未登记的隐藏文件: captagent/.progress-closed, lsof/.recipe-marker, ...
Junk Files: 3
JC_RESULT=fail
L0_RESULT=fail: junk_check failed
L1/L2/L4/L5_RESULT=skip: blocked_by_JC
Pass rate: 0.0% (0/1)
```

命中文件全部属于**其他库**、不在 origin/main tree、与本 PR 零关系（本机实测定性：
`git cat-file -e origin/main:<file>` 均失败 → 非基线合入，仅本地/历史跟踪残留）。

## 触发条件

新库分支从 origin/main 创建、零提交（三点 diff 为空）、无 pr.diff →
`junk_check.sh` 落 **full 模式**（`git ls-files` 整仓扫描），命中共享仓库上游历史遗留
的其他库基线跟踪垃圾（flatcv / goaccess / captagent / lsof / scudo-malloc / stb_image）。

## 方案：prdiff 作用域（本 PR 新增，CI 同款）

junk_check.sh 模式优先级：**prdiff（pr.diff 存在）→ incremental → full**。
CI 中 buildbot checkout-pr 提供 pr.diff，所以 CI 从不整仓扫描。本地显式给出本 PR
文件清单即可进入 prdiff 模式：

```bash
# 生成仅含本 PR 新增文件的 pr.diff
for f in $(git status --porcelain archives/l/libjpeg-turbo/3.0.4/ | awk '{print $2}'); do
  echo "+++ b/$f"
done > /storage/Users/currentUser/tmp/libjpeg-turbo-r01/pr.diff

# 校验：Junk Files: 0
JUNK_PR_DIFF=/storage/Users/currentUser/tmp/libjpeg-turbo-r01/pr.diff bash ci/scripts/junk_check.sh

# 带作用域重跑 finish → W3 通过
JUNK_PR_DIFF=$PD python3 scripts/ohc-run.py finish libjpeg-turbo 3.0.4 built
```

优点（相比 DRAFT-dr_mp3 的 git rm --cached 索引隔离）：
- 不修改其他库文件的索引、无 `git rm --cached`、无 `git add -f`、无恢复审计；
- 与 CI prdiff 行为一致，本地结论直接对齐 CI 判定；
- 无需把其他库基线垃圾搬进/移出索引，原子性与可审计性更好。

## 验证

- junk_check 全仓自检：Junk Files: 3 → FAIL（命中 6 个其他库文件，JC1/JC3/JC5）
- prdiff 模式自检：**Junk Files: 0, JC_RESULT=pass**
- finish3/finish4 带 JUNK_PR_DIFF 重跑：W3 本地 CI 模拟通过，`.ci-result.json` exit_code=0
- 证据日志: finish.log / finish2.log / finish3.log / finish4.log

## 适用边界 / 反例

- 适用：新库零提交分支、pr.diff/incremental 均不可用、JC full 模式误伤时；
  本 PR 已产生全部新增文件且不涉及框架文件。
- 反例：当前库自身确有垃圾文件（如误提交的 packaging/*.tar.gz、.staging-verified）时
  必须真实清理（E256），不得用 prdiff 作用域掩盖当前库自身问题；框架文件改动需单独 PR。
- 关系：similar_to DRAFT-dr_mp3-0.7.2-baseline-noise-isolation（同触发、异方案）、
  DRAFT-kdbusaddons-baseline-noise-isolation、E256（二进制提交被拦截）。

## 关系

- similar_to: DRAFT-dr_mp3-0.7.2-baseline-noise-isolation, DRAFT-kdbusaddons-baseline-noise-isolation, E256
- 差异：本条目提供更高保真的 prdiff 作用域替代解，覆盖"仅需通过 W3 且不想动其他库索引"的场景