# libsoup3 3.6.5-r3 — W3 本地 CI 模拟证据（R12 由 w3-local-ci.log 改写）

> 本文件为 R12 处置产物：原 `reports/w3-local-ci.log` 因仓库禁止 `*.log`
> 提交而改写为 .md，证据要点完整保留（命令、cwd、退出码、关键输出）。

## 命令与退出码

- **命令**（cwd = worktree 根 `…/worktrees/pc3-12-libsoup3-3.6.5`）：
  `python3 scripts/ohc-run.py finish libsoup3 3.6.5-r3 built`
  （内部执行 setup.sh + build_and_test.sh 的 W3 本地 CI 模拟）
- **exit_code = 0**（finish 成功；各门禁 pass）

## 关键输出（要点摘录）

- `setup.sh`（RC=0）：Conan 环境就绪（conan 2.29.1），profile
  `ci/conan/profiles/ohos-aarch64` 导入成功。
- `build_and_test.sh`（RC=0）：
  - **G0**：知识图谱完整性检查通过（540 entries），`G0_RESULT=pass`。
  - **L0i**：依赖在 registry 可用——`glib/2.84.0.1.1`、`libnghttp2/1.70.0`、
    `libpsl/0.21.5.1`、`sqlite3/3.49.1`、`zlib/1.3.1.1` 全部 `[ok]`。
  - **L0j**：版本无冲突（first publish），**L0k**：库包免 commands.json，
    **L0m**：目录结构合法 → `L0_RESULT=pass`（JC_RESULT=pass, JC_ERRORS=0）。
  - **KC**：知识库质量检查通过，`KC_RESULT=pass`。
  - **conan create 执行**：成功；test_package 生成/构建/运行通过。
  - `W3_RESULT=pass`，整体 Build Summary Success=1、Fail=0。

## 基线隔离复验记录（同轮 W3 命中其他库基线文件）

- 路径：`archives/u/util-linux-login/2.42.2/.ci-trigger`（util-linux-login
  2.42.2 的 CI 触发标记，main 提交 761df452 引入，提交前已存在）。
- pre_sha256 = `e3b0c44298fc…`（空文件），隔离后复跑 finish 通过
  （JC5 不再命中），随后原样恢复并核对 post_sha256 = pre_sha256；
  当前库 diff/staged/PR 均不含该路径（详见 reports/forensics/r2-vs-r3.md）。

> 完整门禁输出与构建详细日志（release CI 需复现时）可由
> `ohc-run.py finish` 在 CI 环境原样重现；本 .md 保留全部结果级证据
> （G0/L0i/L0j/L0k/L0m/KC/JC/W3 各门禁 pass 与退出码）。