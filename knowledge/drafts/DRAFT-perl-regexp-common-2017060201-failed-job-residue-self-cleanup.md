# DRAFT-perl-regexp-common-2017060201-failed-job-residue-self-cleanup

## 使用说明

共享真机设备上，**创建失败/中断的隔离 job 残留目录（数百 MB～数 GB、数万小文件）
会把 HMDFS 剩余 inode 耗尽**，导致后续所有任务（包括其他人的）在复制仓库时报
`No space left on device`，而 `df -h` 看起来还有容量。本文给出 job 生命周期
的自清理责任与检查流程。与 DRAFT-nift-3.0.3（复用仓库+最小传输）互补：
nift 讲"少占"，本文讲"用了必还"。

## 适用范围

- 场景：`ohos-prepare-isolated-conan-job.sh` 创建中断（ssh 超时、Ctrl-C、cp 中途
  No space left）；任何在设备 `$HOME/ohos-users/<user>/` 下建目录的流程
- 主体：job 创建者本人；只允许清理**自己本次会话创建的**残留，禁止删除他人 job
- 不适用：已完成且需要保留日志证据的 job（按项目约定保留期处理）

## 输入 / 输出定义

- 输入（症状）：
  1. prepare 脚本 `cp: ...: No space left on device` 且失败点随时间推移
  2. `df -h` 显示有空间（HMDFS 容量与 inode 分离，需 `df -i`；部分系统
     `df -i` 不可用时以"最近是否有中断 job"作为判据）
  3. 设备上存在以自己 job 名命名、但 `logs/` 为空或缺 `run-conan-heavy.sh` 的目录
- 输出（动作）：
  - 确认归属后 `rm -rf <自己的残留job目录>` 并复查创建是否成功
  - 把"清理→重试→成功"记录进 notes，不含敏感路径信息

## 示例

本轮实例（perl-regexp-common-2017060201-20261004）：

```sh
# 1. job 创建在 cp archives/d/* 中途失败，残留 818MB / 数万 inode
du -sh $HOME/ohos-users/codex/perl-regexp-common-2017060201-20261004   # 818M
# 2. 只删自己刚创建的目录（禁止通配他人）
rm -rf $HOME/ohos-users/codex/perl-regexp-common-2017060201-20261004
# 3. 重新 prepare → 成功（repo_status=ready）
```

审查/操作清单：
1. prepare 失败后**立即**检查并清理自己的残留，再排查其他原因；
2. 残留判据 = 目录名匹配本次 job 名 + 缺少 `run-conan-heavy.sh`；
3. 清理只针对精确路径，禁止 `rm -rf $HOME/ohos-users/codex/*`；
4. 重试成功后在 notes 记录"残留已清理"，供设备容量审计追溯。

## 本轮证据

同一设备上首次 prepare 在复制 archives/d/* 时 No space left（残留 818M）；
自清理后同参数重试 `repo_status=ready`，最终 shadow CI 全绿。
