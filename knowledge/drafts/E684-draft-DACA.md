# E684 — OHOS 单文件 Perl 脚本包适配套路（shebang / env-perl + lang-preflight 人工复核）

## 错误特征

- 上游直执时报 `bash: ./mencal: /usr/bin/perl: bad interpreter: No such file or directory`（rc=126，实测）；
- `lang-preflight` 返回 `detected_language: "other"`、`source_stats: "无源文件可统计"`（无扩展名单文件脚本）；
- 运行期 stderr 固定两行 `Can't exec "locale": No such file or directory at mencal line 334` + `Use of uninitialized value in split`（缺 `locale` 命令时的优雅降级噪声）。

## 触发条件

- 构建系统: 无（system: none——发行物仅单文件脚本 + 许可证 + README）
- 阶段: patch / lang-preflight / test_package（直执验证）

## 根因分析

1. 设备与 CI worker 的 perl 都在 HNP 路径 `/data/service/hnp/bin/perl`（5.42.0，短 PATH 实测可得），`/usr/bin/perl` 不存在 → 上游固定路径 shebang 直执必败。
2. `#!/usr/bin/env perl -w` 不可行：toybox `env` 不支持 `-S`（实测 `env: Unknown option 'S perl -w'` rc=125），shebang 参数只能整串当一个 argv；实测去掉 `-w` 前后 stdout/stderr 行为一致。
3. `lang_detect` 只按扩展名与构建系统统计、不嗅探 shebang → 无扩展名单文件脚本恒判 `other`；若按真实语言 `--lang perl` 传参，会触发假 `env_unsupported` 终态写入 result 草稿链（污染共享槽），而 device-facts §4.2 明文「误判不构成终止任务的依据，人工复核留证」。

## 解决方案

### 推荐方案

1. **shebang**：`.work` 内改首行为 `#!/usr/bin/env perl` → `track-edit add <软件> <版本> <文件>` 登记 → `refresh-patch --auto` 产补丁并在 conandata 自动登记；`build()` 加守卫断言（首行不符即 `RuntimeError`）防补丁静默失效假绿。
2. **语言门禁**：先 `file` + `head -1` 人工复核定真实语言，再以 `--lang other` 取 rc=0 过门禁；真实语言证据三处披露（notes 问题表、`feedback/pending/`、本草稿），编排方裁决确认（2026-09-23 mencal 批次）。
3. **测试与产物**：`build()` 只做安装树装配（`system: none`）；`test_package` 必须断言**直执**（证明 shebang 生效）+ `-V` 版本串；运行期噪声只断言 stdout，不假设 stderr 为空；测试临时目录走 `TMPDIR` 链（`$TMPDIR` → `$HOME/tmp` → `/tmp`）并 `trap` 清理，禁止落 `PWD`（会污染工作区提交面，mencal 实测踩中）。

### 禁止做法

- ❌ 禁止把 lang-preflight 的 `other` 直接改传 `perl` 硬吃 rc=2 假终态（污染 result 草稿链，为工具缺陷付任务代价）。
- ❌ 禁止用 `#!/data/service/hnp/bin/perl -w` 写死设备路径（worker 可移植性差，非官方惯例）。
- ❌ 禁止在 test.sh 里用 `PWD` 当工作目录往包目录写临时文件。

## 验证

```bash
# 复现（未打补丁的 pristine 副本，预期 rc=126 bad interpreter）
cd /storage/Users/currentUser/tmp/mencal-3.0/w0src/mencal-3.0 && head -1 mencal && ./mencal -V; echo rc=$?
# 修复后（安装树内直执 + 版本串，预期 rc=0 且 Menstruation calendar 3.0）
conan create /storage/Users/currentUser/ws/worktrees/mencal-3.0/archives/m/mencal/3.0 \
  -pr:h=/storage/Users/currentUser/ws/worktrees/mencal-3.0/ci/conan/profiles/ohos-aarch64 \
  -pr:b=/storage/Users/currentUser/ws/worktrees/mencal-3.0/ci/conan/profiles/ohos-aarch64 --build=missing
```

## 关联条目

- 相关: abi-compliance-checker 2.3（同型先例，`system: perl` + shebang→env perl，已 published）
- 同批披露: `notes.md` 问题表 #1/#2/#3、`feedback/pending/2026-09-23-mencal-3.0.md`
