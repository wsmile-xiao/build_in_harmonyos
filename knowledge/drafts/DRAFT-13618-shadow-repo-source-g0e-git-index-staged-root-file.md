# DRAFT-13618-shadow-repo-source-g0e-git-index-staged-root-file：真机 shadow CI 的 G0e 按 git 索引查白名单，--repo-source 连带继承上游 repo 的暂存文件

> Source: libmicrodns 0.2.0 适配（真机 shadow CI r3-r5 轮实测，2026-09-27）
> 对应：`knowledge/drafts/DRAFT-13618-shadow-repo-source-g0e-git-index-staged-root-file.kv`

## 现象

真机 shadow CI（`ohos-prepare-isolated-conan-job.sh --repo-source` 创建的隔离 job）
跑 `ci/conan/build_and_test.sh`，G0e 稳定报：

```console
[fail] G0e: 根目录存在非白名单文件（仅允许 .gitignore|.gitattributes|...）:
        .ci-result.json
L0_RESULT=skip: blocked_by_G0
```

诡异之处（三重矛盾，极易误判为"闹鬼"）：

1. 工作区 `ls -a` **看不到** `.ci-result.json`——它根本不在磁盘上；
2. 部署 3 秒轮询 watcher 监控该路径，**永远抓不到**文件出现；
3. 文件"自己会消失"——上一轮还在报，下一轮手动 `ls` 又没了（实际是不同 job 的
   repo 副本状态差异造成的错觉）。

## 根因

G0e 的枚举命令是：

```sh
git ls-files --full-name | grep -v '/'
```

这读的是 **git 索引（staged 列表）**，不是工作区目录。而 `--repo-source` 复制
repo 时是**整目录复制（含 `.git`）**：上游 repo-source（其他包的 agent 工作区）
若曾把 `.ci-result.json` 之类的根目录文件 `git add` 过而未清掉，这条 staged
记录就原样进入新 job 的索引——工作区没有文件，索引里有名字，G0e 照拦不误。

**典型时序陷阱**：shadow 设备登录 PATH 没有 git/bash（在 `/data/service/hnp/bin`）。
git 不可用时 `git ls-files` 报 `permission denied: git`、命令替换输出为空，
G0e 反而"通过"。先修 PATH、git 能跑了，索引问题才暴露——于是看起来像
"修一个坑冒出一个新坑"，实际是同一链条的两环。

## 方案

主方案：在 job 的 repo 副本里把残留条目从索引摘除（只动本地副本，不涉真实仓库）：

```sh
export PATH=/data/service/hnp/bin:$PATH
cd <job>/repo/build_in_harmonyos
git ls-files --full-name | grep -v '/'   # 列出全部根目录 staged 条目
git rm --cached .ci-result.json          # 对非白名单条目逐个摘除
```

然后重跑 `git ls-files --full-name | grep -v '/'` 确认只剩白名单文件
（`.gitignore|.gitattributes|BUILD.gn|CONTRIBUTING.md|KNOW_YOUR_WHY.md|LICENSE|
README.md|SKILL.md|SUMMARY.md|oh-package.json`），再启动 runner。

**不要**用 `rm` 删工作区文件来"修"——文件本来就不在工作区，对症的是索引。

备选：换一个近期、索引干净的 job 作 `--repo-source` 重建隔离 job（治标，无法
保证新 source 索引干净）。

## 验证

libmicrodns 0.2.0 真机 shadow CI 实测：r3/r4/r5 连续三轮被
`G0e: .ci-result.json` 拦截；`git rm --cached` 后 r6 一次通过
（G0/G0e/KC/JC/L0/L1/L4/L5 全 pass，exit code 0，上游测试 1/1、
test_package 8/8）。

## 关联知识

- 避坑指南 §8（设备 PATH 缺 git/bash → 加 `/data/service/hnp/bin`）是本条目的
  前置环节；两坑叠加时的时序见根因一节。
- 同族风险：任何"以 git 索引/`git status` 为数据源的门禁"在 `--repo-source`
  复制场景下都会继承上游工作区状态，不止 G0e 一处。
