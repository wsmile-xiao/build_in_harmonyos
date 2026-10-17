# DRAFT-maxflow-3.0.5-isolated-job-cipackages-default — 手动创建隔离 job 漏传
# --package 时 env.sh 静默带着 apache-arrow 默认包路径，会跑错包

> Contributor: codex | Status: Draft | Updated: 2026-09-27
> Source event: maxflow 3.0.5 真机 shadow CI 准备阶段（archives/m/maxflow/3.0.5）

## 错误特征（静默，无报错）

手动执行 `ohos-prepare-isolated-conan-job.sh --user codex --job <名> --repo-source <repo>`
后，`<job>/env.sh` 里是：

```sh
export CI_PACKAGES='archives/a/apache-arrow/24.0.0'   # ← 不是你的包！
```

runner 会把它原样传给 `build_and_test.sh`——**跑的是 apache-arrow，不是你的库**。
轻则浪费一次排队窗口，重则污染设备上的制品缓存与结论记录。

## 根因

`ohos-prepare-isolated-conan-job.sh` 的 `--package` 是可选参数且带字面默认值
（脚本 --help 原文）：

```text
--package PATH       CI package path. Default: archives/a/apache-arrow/24.0.0.
```

脚本 --help 与 outputs 里不回显最终 CI_PACKAGES，创建成功输出
（job_base/env_file/run_file/ci_repo_root/conan_home/repo_status）也不含它，
遗漏毫无提示。

## 解法（创建后强制自检一步）

1. 创建 job 后、启动 runner 前，**必查**：

```sh
grep CI_PACKAGES "$HOME/ohos-users/codex/<job>/env.sh"
# 必须等于自己要测的包路径，否则改掉
```

2. 包在本机时：不传 --package 创建 job → scp/base64 传包 → 解压进
   `<job>/repo/build_in_harmonyos/archives/...` → 修正 env.sh 的 CI_PACKAGES
   指向该路径（HMDFS 上用 base64 重写或 `sed` 后 `cat` 回写，勿依赖 sed -i）；
3. 包已在设备上时：直接传 `--package archives/<首字母>/<库>/<版本>`。

## 查重（B1 证据摘要）

- 检索词：`CI_PACKAGES` / `isolated-conan-job` / `隔离 job`（knowledge/ 全目录）。
- E253、DRAFT-aghermann：CI_PACKAGES 只作为**手动模拟时显式传参**的用法示例
  出现，未提 prepare 脚本默认值陷阱；
- 设备脚本 `--help` 实测（2026-09-27）：Default: archives/a/apache-arrow/24.0.0。
- 新增价值：填补"手动创建隔离 job 的静默错包"运维盲区——这是唯一一个
  "CI 显示全绿但测的不是你的包"的失败模式，比构建失败更隐蔽。

## 验证证据

- maxflow job 创建后 env.sh 实测含 `CI_PACKAGES='archives/a/apache-arrow/24.0.0'`
  （未传 --package），修正后 r1-r6 全部以
  `CI_PACKAGES received: archives/m/maxflow/3.0.5` 开跑。
