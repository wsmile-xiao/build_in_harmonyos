# DRAFT-shadowci：真机 shadow CI runner 的 PATH 丢失 /data/service/hnp/bin，KC 门禁报 "permission denied: bash" 并连锁 blocked_by_KC

> Draft（未 promote）— 来源于 fathom 1.0 适配 shadow CI（job fathom-1.0-20260927，2026-09-27）
> 对应 `.kv` 文件同 stem：`DRAFT-shadowci-runner-path-missing-hnp-bin-kc-blocked.kv`

## 症状

`run-conan-heavy.sh` 一轮里包结构类门禁全过，但在 KC 步骤死掉：

```
[step] L0m: Checking directory structure (R39/L0m-4/L0m-5)...
        [ok] L0m: directory structure valid
[ok] L0: All quality gate checks passed

[step] KC: Knowledge graph quality check...
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build
L0_RESULT=fail: knowledge_check failed
L1_RESULT=skip: blocked_by_KC
L2_RESULT=skip: blocked_by_KC
L4_RESULT=skip: blocked_by_KC
L5_RESULT=skip: blocked_by_KC
```

早前 G0e 步骤还会有一条**非致命**的 `build_and_test.sh:164: permission denied: git`
（G0e 容忍 git 缺失继续走）。现象的欺骗性在于：**配方和包本身没有任何问题**，
失败完全来自设备运行环境漂移；而 "permission denied" 字样让人误以为
是文件权限或 HMDFS 执行位问题。

## 根因

设备上 bash/git/clang/conan 等工具的真实可用入口在 `/data/service/hnp/bin`
（bash 5.3、git 2.45.2、clang 15.0.4 实测）。runner 每次运行时从登录环境
继承 PATH，`env.sh` 只前置 python-user/.local 两个目录。

- 成功 run（如 15:48/15:54 的 job）的 `ohos-test-runs/<run-id>/logs/env.txt`
  里 PATH **含** `/data/service/hnp/bin`；
- 失败 run（16:10）的 env.txt PATH **不含**它——设备默认 PATH 在两个时刻
  之间发生了漂移（不是本 job 造成的）。

PATH 里没有 bash 时，zsh 对 `bash xxx.sh` 报 "permission denied: bash"。
另外 `$HOME/ohpc-ci-shadow/python-user/bin/git` 是一个 HMDFS 上的 67 字节
包装脚本，**HMDFS 分区上即使 -rwxr-x--- 也不可执行**，会抢在 hnp/bin 之前
被解析到——所以修 PATH 时插入位置必须保证 hnp/bin 排最前。

## 方案

只改**自己 job** 的 `env.sh`（job 局部文件，非公共设施），在**文件末尾**
追加一行前置（末尾追加才能压过 env.sh 前文对 python-user 的前置）：

```sh
export PATH=/data/service/hnp/bin:$PATH
```

验证：

```sh
sh -c ". \"$JOB/env.sh\"; command -v bash git clang conan; bash --version"
# 期望全部解析到 /data/service/hnp/bin/...，bash 5.3.0
```

然后重跑 `run-conan-heavy.sh` 即可全绿。

## 诊断套路（可复用）

1. runner 返回 1 且 stdout 只有退出码 → 去设备 `ls -dt "$HOME/ohos-test-runs"/*/`
   找本包 run 目录，读 `logs/stdout.log`（完整门禁输出在这里，job 自己的
   `logs/` 只有大文件类产物）。
2. 疑似环境问题 → **对比成功 run 与失败 run 的 `logs/env.txt` PATH 差异**，
   一眼定位丢了哪个目录。
3. "permission denied: <工具名>" 先分辨两种情况：HMDFS 分区文件不可执行
   （换 /data/service 下的真身）vs PATH 没解析到（补 PATH）。
