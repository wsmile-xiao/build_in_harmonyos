# DRAFT — W3 junk_check 回退整仓扫描：无关历史基线阻塞当前库适配

## 错误特征

HarmonyOS PC 本地 W3 `run_local_ci` 模拟（`ci/conan/build_and_test.sh` 内嵌
`junk_check.sh`）在本库 diff 为空（本地开发分支 HEAD 与 origin/main 一致、
尚未 commit）时回退到 **full 模式整仓扫描**（`git ls-files`，本仓 48173 个
文件），把其他库历史上已提交的垃圾/状态文件当成阻塞项：

```
[step] JC1: 运行时状态文件检测...
[FAIL] JC1: 1 个运行时状态文件被跟踪:
       archives/f/flatcv/0.3.0/.staging-verified
[step] JC3: 源码 tarball / 打包产物检测...
[FAIL] JC3: 1 个 tarball/打包产物被跟踪:
       archives/g/goaccess/1.10.2/ncurses-headers.tar.gz
[step] JC5: archives 隐藏文件白名单检测...
[FAIL] JC5: 6 个 archives 下未登记的隐藏文件: ...
JC_RESULT=fail → L0_RESULT=fail: junk_check failed
```

结果：`libpopcnt` 自身的 Adapt 已通过（conan create G0-G4/L2/L4/L5 PASS、
test_package + OHOS 消费者 PASS、W2 原子性 PASS），却因**其他库**的已提交
历史垃圾路径被整仓扫描命中而整体 `W3/finish` 失败。

## 触发条件

- 构建系统: 任意（header-only 库同样触发）
- 阶段: W3 本地 CI 模拟 / CI `build_and_test.sh`（junk_check 步骤）
- 前置: 当前库 diff 为空或 `git diff origin/main...HEAD` 无 ACMR 变更
  → `JUNK_CHECK_MODE` 回退 full（`git ls-files`）
- 平台: HarmonyOS PC（本地执行端，未 commit 的 adapt 分支）

## 根因分析

1. `junk_check.sh` 检查范围三优先级：prdiff（PR 文件清单）→ incremental
   （`git diff origin/main...HEAD`）→ full（`git ls-files` 整仓）。
2. 执行端在适配过程中**不 commit**（任务边界禁止），分支 HEAD 与 origin/main
   一致 → `git diff origin/main...HEAD` 为空 → 静默回退 full 整仓扫描。
3. full 扫描把**其他库历史已提交**的 `.staging-verified`、`.progress-closed`、
   `.recipe-marker`、`.manifest-complete`、打包 tarball 等路径全部拉入
   CHECK_FILES，任意一条命中 JC1/JC3/JC5 即阻塞整个 W3。
4. 这些路径既非当前库产生、也不在当前库 diff 内，却因整仓扫描连坐阻塞。

## 修复方案（有界、不改当前库配方）

- W3/junk_check 的作用域应**有界到当前库 diff 检测**：仅对当前库
  `archives/{letter}/{name}/**`（或 PR 文件清单）执行垃圾检查，不回退整仓扫描。
- 对确属其他库历史基线的噪音：采用**精确 baseline-noise 隔离/恢复证据**
  （记录发现命令、tracked 状态、提交基线、隔离前/后 SHA-256），在 W3 豁免
  验证通过后原样恢复，并证明该路径不属于当前库 diff。
- 禁止通配符/全局 ignore、删除无关库、或改动当前库配方来掩盖框架/基线问题。

## 验证

- R03 实测：精确隔离 7 个其他库基线路径（flatcv/.staging-verified、
  goaccess/ncurses-headers.tar.gz、captagent/.progress-closed、
  lsof/.recipe-marker、scudo-malloc/.manifest-complete+.progress-closed、
  stb_image/.manifest-complete）后，libpopcnt PR-diff 作用域下 junk_check
  不再拦截；恢复后 7 路径哈希与隔离前一致，git 原子性回到基线。
- 结论：libpopcnt 自身无剩余 W3/finish 缺陷，共享 junk_check 整仓回退为
  治理问题（本草稿），不通过本库配方掩盖。

## 适用边界与查重差异

- 适用: W3 `junk_check` 在本库 diff 为空时回退整仓扫描并命中其他库历史
  垃圾路径的场景；任何 diff 为空/未 commit 的本地适配分支均可能触发。
- 差异: 现有知识聚焦"当前库产生的垃圾文件"（.build-closed、CMakeUserPresets、
  ghfast-bak 等），本草稿聚焦"整仓扫描把无关历史基线连坐阻塞当前库"，
  且给出有界的隔离/恢复豁免证据流程，不主张删除或全局忽略。
- 未泛化: 不改变其他库归档、不修改共享脚本、不删除任何路径。
