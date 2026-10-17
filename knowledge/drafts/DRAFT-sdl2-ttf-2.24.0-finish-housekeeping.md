# DRAFT-sdl2-ttf-2.24.0-finish-housekeeping — OHOS 本地交付收尾与 finish/W3 共享基线噪音（路径 B 候选）

> 配对条目：`knowledge/graph/draft/DRAFT-sdl2-ttf-2.24.0-finish-housekeeping.kv`
> 来源：sdl2-ttf 2.24.0 R03/R04 本地适配（pc1-46，2026-08-28）

## 问题

在 HarmonyOS PC 本地完成 `ohc-run.py finish` 交付时，遇到两个相互独立的共享基线/框架问题：

1. **W3 整仓 junk-check 被他库基线 tarball 阻塞**
   `finish` step5 的本地 CI 模拟（`ci/conan/build_and_test.sh` → `ci/scripts/junk_check.sh`）在无
   pr.diff、无本地提交（分支相对 origin/main 三点 diff 为空）时回退到 **full 模式**，用
   `git ls-files` 扫描整仓全部被跟踪文件。`origin/main` 中历史遗留的
   `archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`（他库，已被 git 跟踪）触发 JC3
   → 整仓 junk-check FAIL。该文件归属他库，超出当前库授权范围，不可修改/删除 → 本地 W3 无法直接通过。

2. **gen_summary 重复键导致 AttributeError 崩溃**
   `finish` step6 的 `generate_summary`（`scripts/ohc/summary.py` `_parse_yaml_simple`）扫描整仓
   `manifest.yaml`。部分历史 manifest（如 `archives/q/qpdf/12.3.2`、`12.3.2.1`）存在**重复键**：
   同一 key（`knowledge_gained`）先以标量/空列表出现、后以列表再定义，解析器对已存在的字符串值执行
   `setdefault(key, []).append(...)` → `AttributeError: 'str' object has no attribute 'append'`
   → `SUMMARY.md` 无法生成（框架级首错，与本库无关）。

## 根因

- 问题 1：full 模式整仓扫描把「已被跟踪的历史基线 tarball」误判为待提交 junk；该文件不在当前库授权范围。
- 问题 2：简易 YAML 解析器未处理「同一 key 先标量后列表」的重复定义，对已存在标量执行 `.append()` 崩溃。

## 最小本地解决 / 边界

1. **基线噪音隔离（仅 index 层，任务授权）**：
   - `git rm --cached <基线路径>`（保留工作区文件、不改内容）
   - 隔离状态下重跑完整 `finish`/W3 → `JC_RESULT=pass`、Pass rate 100% (1/1)、`.ci-result.json` exit_code=0
   - **无条件恢复**：`git add -f <基线路径>`（该路径在 `.gitignore` 中，需 `-f` 还原历史被跟踪条目）
   - 校验恢复后 index blob 与 SHA-256 与隔离前一致；该路径不进入最终 diff/PR
   - 判定：当前库无任何失败 → 报告 `baseline_noise_exempted`（外部基线豁免）
2. **gen_summary 框架首错**：不改他库 manifest（越权）。临时在 `_parse_yaml_simple` 增加
   `_ensure_list()` 防御（对已存在的标量值重建空列表再 append），重跑受影响验证，
   然后**无条件** `git checkout -- scripts/ohc/summary.py` 还原，报告前后 sha256 与还原证据。
   框架路径绝不进入最终交付。

## 验证

```bash
# 问题 1（隔离 → 重跑 → 恢复 → 校验）
git rm --cached archives/g/goaccess/1.10.2/ncurses-headers.tar.gz
python3 scripts/ohc-run.py finish sdl2-ttf 2.24.0 published   # W3: JC pass, 100% (1/1)
git add -f archives/g/goaccess/1.10.2/ncurses-headers.tar.gz
git rev-parse :archives/g/goaccess/1.10.2/ncurses-headers.tar.gz  # 与原 blob b154073f... 一致
sha256sum archives/g/goaccess/1.10.2/ncurses-headers.tar.gz       # bf58efee... 与隔离前一致

# 问题 2（复现 → 临时修复 → 重跑 → 还原）
python3 - <<'PY'
import sys, os
sys.path.insert(0, os.path.abspath('scripts'))
from ohc.summary import generate_summary
generate_summary(pdir='.')   # 修正前 AttributeError；修正后 OK（输出 ~363KB SUMMARY.md）
PY
# scripts/ohc/summary.py 修正后 sha256=b4409a1c...，git checkout 还原后 sha256=d4d14df2...（与原始一致）
```

## 可复用适用性

- **适用**：任何在本仓库做本地 finish/W3 交付、且遇到「整仓 junk-check 被他库基线 tarball 阻塞」或
  「gen_summary 因重复 manifest 键崩溃」的库；以及任何需要把「外部基线噪音」与「当前库真实失败」区分开，
  从而豁免当前库的场景。
- **边界**：隔离仅限 index 层、必须无条件恢复并留证据；他库文件/框架文件绝不进入最终交付；
  不创建/更新 PR/Issue、不推送远端、不写 Conan remote、不访问分析端 `/mnt/e` 模板；
  真正的整仓修复（清理 origin/main 遗留 tarball / junk_check 改 prdiff 范围）由共享框架维护方完成。
- **查重差异**：与 `DRAFT-jc6-origin-main-stale-ref` 不同——该条目是 origin/main 引用过期导致
  incremental 模式误报；本条目是 full 模式扫描历史跟踪 tarball 与 gen_summary 重复键崩溃，根因与修复路径均不同。

## 关联

- 任务：sdl2-ttf-2.24.0 R03（baseline_noise_exempted）/ R04（本收尾与路径 B 审计）
- 归档：`archives/s/sdl2-ttf/2.24.0/`（conanfile.py / conandata.yml / patches/ / test_package/ / reports/）
