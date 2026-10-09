# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_b0e64d97.md`

---

## 背景

- **软件名称**: shfm
- **版本**: 0.4.2
- **构建日期**: 2026-10-04
- **构建系统**: custom（单文件 POSIX sh 脚本，没有构建系统；自动采集没有替换构建系统占位符，已手工更正）
- **上游仓库**: https://github.com/dylanaraps/shfm（自动采集为“未知”，已更正）
- **适配路径**: 路径 B（知识库扩展：1 个补丁 + 1 份知识草稿；自动采集写成“路径 A（基础适配，无补丁）”，已更正）
- **补丁数量**: 1（`patches/0001-shfm.patch`，自动采集为 0）
- **编译依赖**:
无 Conan 依赖；运行期仅需系统工具 POSIX sh、`[`、`printf`、`dd`、`stty` 与控制终端
- **最终状态**: built（本地 W3 通过；本报告在建 PR 之前定稿）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交前的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 构建系统被误判为 autotools；conanfile/conandata/test_package 三个模板均“不可用”；生成的 `manifest.yaml` 全是占位符 |
| build | 手工打包 + 补丁 | 成功 | 构建系统: custom（脚本，无编译）；发现并修复 cd-on-exit 在 mksh/bash/zsh 下 stdout 为空 |
| conan-verify | 配方验证 | 通过 | G1/G2/G3 一次通过，G2 内含 `conan create` 与 test_package（pty 会话 + aarch64 消费者经 qemu 运行） |
| finish | 归档收尾 | 部分完成 | W2/R36/W3 通过；G0 clean-verify、gen_summary、`packaging/` 检查是与本包无关的框架噪声，finish 因此以 rc=1 结束 |
| submit | PR提交+AI检视+CI | 未执行 | 本报告随 PR 一同提交，写报告时 PR 尚未建立；AI Review: — |

### 失败与问题

1. `init-build` 把没有任何构建文件的脚本包判为 autotools，三个模板“不可用”，`manifest.yaml`/`notes.md` 全是占位符，只能手写 `application` 配方（与已合入的 `unfoo` 同形态）。
2. 上游行为缺陷（非 SKILL 缺陷，但是本次的主要发现）：shfm 的 cd-on-exit 在 mksh、bash、zsh 下取不到输出，只有 dash 正常；已打补丁并沉淀为知识草稿。
3. shfm 在没有控制终端时连 `--version` 都无法启动（`main "$@" >/dev/tty`），test_package 必须自己建 pty。
4. `finish` 的 W3 之后工作区出现副作用：`conandata.yml` 的 url 被改写成 gh-proxy.com 镜像列表、`conandata.yml.orig` 残留、仓库根多出未被忽略的 `.build-cache/`，`manifest.yaml` 的人工 `patch_classification` 被覆盖回 `type: auto / guard: pending` 并丢掉 `knowledge_gained`。提交前必须 `git checkout --` 还原，否则 PF7 会拦 gh-proxy.com。
5. `finish` 的 G0 clean-verify 对没有 `configure` 的脚本包报 `configure 失败 (exit 127)` 与 HANDOFF，但 W3 实际通过。

### 知识图谱使用情况

- **引用知识条目**: E037、E165、E435（确认 OHOS 的 `/system/bin/sh` 是 mksh、bash 在 hnp 目录；用于判断受影响的 shell）
- **新增知识草稿**: 1 份，`E14731-draft-6E2B`（`knowledge/drafts/`）
- **引擎命中情况**: `engine` 对 `cannot create /dev/tty` 与 `stty: Inappropriate ioctl for device` 两条报错的命中（E249、E161）均与本问题无关；`draft-review` 判 `create`，最近条目 E239（0.09）。草稿目录共 2869 个 .kv，自动采集的这个数字统计的是整个目录，不是本 PR 的新增草稿
- **测试统计**: 上游用例 0（无 `tests/`，仅 CI 工作流 `shellcheck shfm`，原版与补丁版均 rc=0）；test_package 2/2 通过；完整场景在 6 种 shell 调用下补丁版 6/6、原版 1/6（自动采集为总计 0）
- **未覆盖的错误模式**: “被重定向的函数里 `exit`，EXIT trap 的 stdout 因 shell 而异”此前没有条目，已写入草稿

### AI 检视结果

- **检视阶段到达**: 未到达（PR 尚未建立）
- **变更摘要评估**: 不适用
- **检视意见数量**: 0
- **检视意见处理**: 不适用

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`setup.sh` + `build_and_test.sh`：L0、KC、JC 全过，L1a/L1b/L1e 通过，L1e 破坏 `bin/` 后测试确实失败；L2 的 `--version` 因无 tty 报非阻塞告警）
- **远程 CI (PR 校验)**: 未执行
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 1（`finish` 的 G0 clean-verify，框架噪声）
- **重试次数**: 0（`conan-verify`、`finish` 各跑 1 次即过）
- **关键瓶颈**: 没有“脚本工具 + 终端交互 + 消费者用例”的模板，pty 驱动脚本、负向对照和多 shell 矩阵都要从零设计
- **耗时较长的步骤**: 多 shell 复现根因与调 pty 同步点；`conan-verify` 与 `finish` 本身各约 1–3 分钟

---

## 建议

### SKILL 设计改进

1. `scripts/ohc/clean_verify.py:69` 把 `./configure` 写死。没有 configure 的脚本/headeronly/custom 包应跳过 G0，或改成“应用补丁 + `sh -n`”；现在 W3 已通过，`finish` 仍打印 G0 HANDOFF FAIL 并以 rc=1 结束，容易诱导去“修复”不存在的问题。
2. `ci/conan/build_and_test.sh:1029` 在镜像改写前才 `cp conandata.yml conandata.yml.orig`，而 `:1180-1190` 的 EXIT 还原备份的是**已被改写**的文件，所以本地 W3 之后 `git status` 出现 ` M conandata.yml`（url 变成 gh-proxy.com 列表）。应在 EXIT trap 里还原 `.orig`，并把 `.build-cache/` 加入 `.gitignore`。
3. `scripts/ohc/finalize_archive.py:119` 与 `scripts/ohc/finish.py:372-373` 仍检查已废弃的 `packaging/` 和 release/debug tar.gz，每个包都报“缺失项”假告警，建议删除这两项检查。
4. `scripts/ohc/finish.py:337-345` 的 `step6_gen_summary` 吞掉了异常（`'str' object has no attribute 'append'`）却仍把 step 记为完成，应让它失败或修掉该 bug。

### 模板改进

1. `scripts/ohc/init_build.py:78-86` 的 `_guess_build_system` 对没有任何构建文件的目录默认返回 `autotools`，随后 `scripts/ohc/init_archive.py:241-306` 报三个“模板不可用”。建议无构建文件时返回 `script`，并基于 `templates/conanfile-headeronly.py.tmpl` 的变体 C 提供 `application` + `commands.json` 的脚本包模板。
2. 补一个 `templates/test_package-script/`：pty 驱动脚本（`pty.openpty()` + `TIOCSCTTY`、按键与屏幕同步、stdout 管道）+ 把工具输出当作输入的 aarch64 消费者（`CMakeLists.txt`/`consumer.c`）。本次的 `drive_shfm.py` 可直接作为底稿。
3. 生成的版本级 `manifest.yaml` 保留了软件名、构建系统两个花括号占位符与 `sha256: ""`，而 `init-build` 已在 `.orig/.tarball-sha256` 里算出校验和，应直接回填。
4. `refresh-patch --auto` 只能生成 `0001-<文件名>.patch`，并在 `manifest.yaml` 写 `type: auto / platform_only: True / guard: pending`，建议支持 `--name`、`--type`、`--guard`，避免之后人工改 manifest 又被 `finish` 覆盖。

### 自动化补全

1. feedback 骨架在 `lang-preflight` 阶段就生成，之后不再重采：构建系统占位符未替换、上游仓库“未知”（`manifest.yaml` 的 `source.url` 其实可得）、适配路径“路径 A（基础适配，无补丁）”、补丁数 0、测试统计 0、草稿数统计整个目录。建议在 `finish` 结束时用最终的 manifest/patches/test_package 重新采集（`scripts/ohc/feedback.py` 约 :525-526 取值处）。这些字段本次都是手工改正的。
2. `scripts/ohc/utils.py:112-134` 的 `get_agent_id` 每次调用都随机生成，同一次任务里 result.json 的 `agent`、feedback 的 Agent ID、草稿的 `contributor_id` 互不相同。建议第一次生成后落到 `.ohc/` 下复用。
3. `ci/conan/build_and_test.sh:1676-1702` 的 L2 smoke 对必须有控制终端的 TUI 脚本只能报 `--version/--help failed (non-blocking)`；可通过 MANIFEST 声明 smoke 命令，或用 `script -qec` 包一层 pty。
4. `graph add` 不带编号时返回最小空洞，而 `knowledge/drafts/` 里的草稿大量使用 E876、E14721 这类任意编号，容易撞号。建议 `graph add --draft` 自动分配“当前最大草稿号 + 1”。
5. PF8 要求新增软件带 `commands.json`/README/manifest，PF9 又拦不带版本目录层的 `archives/` 路径，新增软件的首个版本必然同时命中；建议在 `preflight.py` 里让 PF9 豁免软件级文件。

### 知识图谱覆盖

- 新增草稿 `E14731-draft-6E2B`：被重定向的函数里 `exit`，EXIT trap 的 stdout 在 mksh/bash/zsh 下仍是 `/dev/tty`，只有 dash 先撤销重定向，导致 cd-on-exit 惯用法 `cd "$(prog)"` 取到空串。建议主编 promote，并与 E435（OHOS `/bin/sh` 为 mksh 的行为差异）、E037 互相引用。
- 建议把 `knowledge/drafts/` 里 pty 驱动 TUI 测试的若干草稿（如 `DRAFT-E5xx-tui-app-pty-test-harness`、`DRAFT-E429-cfm-termios-tui-pty-consumer-test`）合并成一条“TUI 脚本/程序的 pty 测试”正式条目，并补上“无控制终端时 `main >/dev/tty` 直接失败（连 `--version` 也不行）”这一识别特征。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: F4D6
- **生成时间**: 2026-10-04 01:05:39
- **PR 编号**: —
- **Git Commit**: d66f94cc12
