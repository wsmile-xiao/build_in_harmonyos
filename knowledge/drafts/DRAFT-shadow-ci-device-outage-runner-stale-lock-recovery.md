# 共享真机断联后 shadow CI 恢复：nohup runner 死亡判定与 stale 锁安全清理

> 草稿（DRAFT）。与同目录 `DRAFT-shadow-ci-device-outage-runner-stale-lock-recovery.kv` 成对。
> 实证来源：ndppd 0.2.6 shadow CI r1–r3 轮（2026-09-29，设备 48 分钟 + 数小时两次失联）。

## 现象

真机 shadow CI 排队/运行期间设备失联（本地侧 `banner exchange ... Connection timed out`
连刷，ping 也不通）。设备恢复 SSH 后发现：

- nohup 启动的 runner（`run-conan-heavy.sh`）与监控循环**全部死亡**，日志 0 字节
  （连排队信息都没写过——死在排队循环里，从未进入构建）；
- `~/ohos-test-locks/device-global.lock.d/` 目录残留，`holder.txt` **内容为空**；
- 其它会话的新 job 可能卡在这个残留锁上（表现为 LOCK 目录存在但无 holder、无构建进程）。

## 根因

1. **nohup 只防 SIGHUP**：设备重启/断电/OOM 强杀会直接带走进程。共享真机的 runner
   生命周期与设备可用性强绑定，"启动即不管"不可靠。
2. **mkdir 锁无租约**：`ohos-test-runner.sh` 用 `mkdir device-global.lock.d` 原子加锁、
   退出时 rmdir 释放。持锁进程被杀死时锁目录永久残留。恢复后所有人排队等一个
   已不存在的持有者。
3. `holder.txt` 写在持锁之后：进程若在写入前死亡，文件为空——恰好成为
   **"stale 且无主"的可靠判据**（有内容的 holder.txt 才需要比对 PID 存活）。

## 正确做法（恢复后的三步处置）

```sh
# 1) 判定 stale 并清理（只对 holder.txt 为空或 holder_pid 已死的锁动手）
if [ ! -s ~/ohos-test-locks/device-global.lock.d/holder.txt ]; then
    rm -rf ~/ohos-test-locks/device-global.lock.d && echo STALE_REMOVED_EMPTY
else
    PID=$(grep holder_pid ~/ohos-test-locks/device-global.lock.d/holder.txt | cut -d= -f2)
    kill -0 "$PID" 2>/dev/null || { rm -rf ~/ohos-test-locks/device-global.lock.d; echo STALE_REMOVED_DEAD_PID; }
fi

# 2) 重启 runner（继续 nohup；没有更抗断联的替代方案，接受其局限）
J=$HOME/ohos-users/codex/<job>
nohup sh $J/run-conan-heavy.sh > $J/logs/runner-stdout.log 2> $J/logs/runner-stderr.log &

# 3) 用最新 run 目录确认真实状态（job/logs/stdout.log 恒 0 字节，不可作判据）
RUN=$(ls -dt ~/ohos-test-runs/*<库名>* | head -1)
cat "$RUN/logs/exit-code.txt" 2>/dev/null || echo NO_EXIT
```

**本地侧监控纪律**：轮询 ssh 失败时**不要高频重试**（异常表：Connection timed out → 等
恢复，每 2 分钟 Test-NetConnection 探测端口即可）；恢复后先查 `ps` 确认 runner 是否
幸存，死了再重启，**不要盲目重复拉起**（多个排队循环会在锁释放后互相竞争）。

## 避坑

- 清锁只删 `lock.d` 目录本身，别动 `ohos-test-runs/`（别人的排队记录/日志在里面）。
- 重启 runner 前先确认旧进程真死（`ps -ef | grep run-conan`），双活排队 =
  锁释放后两个构建抢同一个 job 目录。
- 设备时间与本地可能差数小时（UTC vs 本地时区），对照日志时间戳时先校准。

## 验证

ndppd 0.2.6：两次断联（~48min + 隔夜）后按此流程恢复，第三次重启即正常拿锁跑完
全部门禁（r7 pass）。stale 锁清理后 edlin 等其它会话的队列也恢复正常推进。
