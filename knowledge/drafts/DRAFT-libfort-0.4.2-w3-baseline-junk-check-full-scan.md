# DRAFT: W3 junk_check 整仓扫描回退导致的基线噪声阻塞（libfort 0.4.2）

## 问题

`finish` 的 W3 本地 CI 模拟（`ci/conan/build_and_test.sh` → `ci/scripts/junk_check.sh`）
在**当前库变更尚未提交**时可能回退到整仓（full）扫描，命中 main 基线中**历史提交遗留**
的垃圾路径，从而阻塞一个本身构建/测试/配方全部通过的有效当前库 Adapt。

### 实测证据（libfort 0.4.2）

- 触发任务: `libfort-0.4.2-r02-adapt-and-local-verification-pc1-18`
- 首次失败: `finish libfort 0.4.2 built` 于 Step5 W3 失败，`Junk Files: 2`，
  `检查模式: full (45335 个文件)`，`JC_RESULT=fail: junk_check failed`
- 命中的基线路径（均为 main 中已 TRACKED 且本任务未改动的历史文件）：
  - `archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`（JC3: 被跟踪的 tarball）
    - 引入提交: `51eae6ae0e feat(goaccess): 1.10.2 适配完成`
  - `archives/s/scudo-malloc/19.1.6/.manifest-complete`（JC5: archives 未登记隐藏文件）
  - `archives/s/scudo-malloc/19.1.6/.progress-closed`（JC5）
    - 引入提交: `4e37f36392 feat(scudo-malloc): 19.1.6 适配完成`

## 根因

`ci/scripts/junk_check.sh` 的扫描范围按优先级判定：

```
pr.diff（PR 文件清单） → incremental（git diff origin/main...HEAD） → full（git ls-files）
```

adapt 阶段所有当前库新文件均为**未跟踪/未 stage** 状态，`git diff origin/main...HEAD`
返回空 → 回退 `full` 模式用 `git ls-files` 整仓扫描 → 命中基线历史垃圾路径。

这是**扫描范围缺少当前库 diff 表示**导致的治理问题，不是当前库自身的构建/配方/测试缺陷。

## 方案（限定当前库 diff 检测 + 精确基线噪声隔离/恢复）

1. **范围限定**：W3 junk_check 应优先基于当前库 diff（如 `git diff -- archives/<lib>/` 或
   当前库文件清单）而非整仓 `git ls-files`，使基线垃圾路径不进入扫描范围。
2. **精确隔离/恢复**：对已证实的基线噪声路径，做临时精确隔离并完整恢复，前后记录
   SHA-256 与 git 原子性，作为豁免证据。libfort 0.4.2 实测命令：
   ```bash
   git rm --cached archives/g/goaccess/1.10.2/ncurses-headers.tar.gz \
             archives/s/scudo-malloc/19.1.6/.manifest-complete \
             archives/s/scudo-malloc/19.1.6/.progress-closed
   python3 scripts/ohc-run.py finish libfort 0.4.2 built   # → W3 本地 CI 模拟通过
   git add -f archives/g/goaccess/1.10.2/ncurses-headers.tar.gz \
              archives/s/scudo-malloc/19.1.6/.manifest-complete \
              archives/s/scudo-malloc/19.1.6/.progress-closed
   ```
   隔离后 W3 通过；恢复后三路径 SHA-256 与隔离前完全一致，git 无 staged/unstaged 差异。
3. **禁止项**：不引入通配符/全局忽略规则；不删除无关库；不修改当前库来掩盖框架/基线问题。

## 验证

- 隔离后 `finish libfort 0.4.2 built` → `✅ W3 本地 CI 模拟通过`
  - 日志: `.atomcode/logs/finish-r03-isolated.log`
- 恢复后:
  - `archives/g/goaccess/1.10.2/ncurses-headers.tar.gz` sha256=`bf58efee849debcfa56ce02f2a099aa25638de6bed90f356fc1018aac59d5e11`（与隔离前一致）
  - `archives/s/scudo-malloc/19.1.6/.manifest-complete` / `.progress-closed` sha256=`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（与隔离前一致）
- 三路径 git 状态恢复为与 HEAD 一致（无 M/D/?? 差异），staged diff 为空

## 适用边界

- 适用于 adapt 阶段（当前库变更未提交）执行 W3/finish、且 main 基线含历史垃圾路径的库。
- 基线噪声豁免成立的条件：被隔离路径须为 main 已提交文件、本任务未改动、不属于当前库 diff。
- 本方案只覆盖垃圾扫描的治理问题；不替代对当前库真实构建/配方/测试缺陷的修复。

## 查重差异

知识库检索 `junk_check|full scan|full-scan|baseline junk|整仓扫描` 无既有条目；
本草稿是首个记录 W3 junk_check full-scan 回退治理问题的条目。
