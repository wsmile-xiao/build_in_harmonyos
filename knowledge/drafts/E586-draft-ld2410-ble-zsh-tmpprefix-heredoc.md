# E586 — zsh here-document 用 TMPPREFIX 而非 TMPDIR：/tmp 只读平台上 CI 门禁假失败

- **状态**: DRAFT（待审）
- **严重度**: 2
- **触发工具**: `zsh` / `build_and_test.sh` / `setup.sh` / `junk_check.sh`
- **阶段**: 测试 / 配置（本地 CI 模拟 W3）
- **来源任务**: ld2410-ble 0.2.0 适配

## 现象

`finish` 的 Step 5/10「本地 CI 模拟（W3）」在 L0 阶段失败，报错与构建本身无关：

```
can't create temp file for here document: read-only file system
```

同一条命令在 `bash` 下正常，换 `zsh` 就挂；`python3` 脚本同样正常。这个
「python 能跑、zsh 脚本挂」的割裂现象是本条的指纹。

## 根因

`zsh` 的 here-document 通过 **`TMPPREFIX`**（默认 `/tmp/zsh`）创建临时文件，
**不读 `TMPDIR`**。而 `bash` 走的是 `TMPDIR`。

鸿蒙 PC worker 上 `/tmp` 是**只读 erofs 挂载**，于是 zsh 脚本里的任何 heredoc
重定向都立即失败。`ci/conan/build_and_test.sh` 内含大量 heredoc（生成预下载片段、
配置片段等），整条 CI 脚本因此在入口处就崩，**报错位置与真实构建问题无关**。

后果：本地 CI 模拟（W3）**假失败**，极易被误诊为依赖缺失或配方问题——两轮
排查方向都被带偏。

## 处置

在调用任何会落到 zsh 的长链路命令（`finish` / `build` / `submit`）之前，
把 `TMPPREFIX` 与 `TMPDIR` **一并**指向可写目录再导出：

```bash
export TMPDIR=$HOME/tmp
export TMPPREFIX=$HOME/tmp/zsh
mkdir -p "$TMPPREFIX"

OHC_PROJECT_DIR=$PWD python3 $SKILL_ROOT/scripts/ohc-run.py finish <pkg> <ver> built
```

`ohc-run.py` 的 `workflow_checks._run` 会复制 `os.environ`，所以**父进程导出即可
穿透到子 zsh**，无需修改框架脚本（协作者铁律：不改 `scripts/`、`ci/`）。

## 探针（建议前置）

与其跑几分钟后才在 L0 挂掉，不如先花一秒探测：

```bash
zsh -c 'cat <<EOF >/dev/null
probe
EOF' || echo "TMPPREFIX 不可写 → export TMPPREFIX=$HOME/tmp/zsh"
```

## 禁忌

- **禁止改 `/tmp` 的挂载**（`mount -o remount` / `chmod /tmp` / `sudo`）：可写性是
  宿主/容器挂载策略，worker 无权也不应改动只读 mount，会污染他人任务并破坏平台
  环境可复现性。
- **禁止把 heredoc 失败误判为 `dependency_missing`**：两者报错形态完全不同，误判
  会导致错误止损上报（R41 要求证据可复核），浪费一次任务并污染依赖缺口统计。

## 影响面

所有在 `/tmp` 只读（erofs / 只读挂载 / 受限容器）的 worker 上、运行含 heredoc 的
**zsh** CI 脚本的任务。对 bash 无影响，故表现为「同一脚本换个 shell 就正常」。

## 验证

设置 `TMPPREFIX` 后重跑，Step 5/10 输出：

```
ℹ️   [1/2] setup.sh...
✅   ✅ setup.sh 通过
ℹ️   [2/2] build_and_test.sh ld2410-ble/0.2.0...
✅   ✅ 本地 CI 模拟通过
```

即 W3 阻塞门禁由「假失败」转为真实评估。
