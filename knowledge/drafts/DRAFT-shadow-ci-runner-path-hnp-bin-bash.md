# DRAFT: 真机 runner 直接启动报 permission denied: bash —— PATH 必须含 /data/service/hnp/bin

- 发现于：tinymembench/0.4 真机 shadow CI r1（2026-09-29）
- 触发面：**所有**隔离 job 的 `run-conan-heavy.sh` 手动启动场景（不限于
  某个库）

## 现象

通过 ssh 手动启动隔离 job：

```sh
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

排队拿锁正常（lock.txt 有 acquired=yes），但 CI 脚本早期即失败：

```
[step] KC: Knowledge graph quality check...
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build
L0_RESULT=fail: knowledge_check failed
L1_RESULT=skip: blocked_by_KC
...
```

stderr 同时可能出现 `build_and_test.sh:164: permission denied: git`。

## 根因

设备上的 bash（及 git、GNU as/ld 等工具链）安装在
`/data/service/hnp/bin`，**不在默认登录 PATH 中**
（登录 PATH 仅 `/bin:/usr/bin:/sbin:/usr/sbin:/storage/Users/currentUser/usr/local/bin`）。
`run-conan-heavy.sh` 继承的是 ssh 登录 shell 的 PATH，CI 脚本里裸调
`bash ci/scripts/knowledge_check.sh` 时找不到可执行的 bash，sh 报
`permission denied: bash`（这正是自检模板「真机坑清单」第 6 条）。

注意区分：`cvsgraph` 条目记录的是 bash 在 HMDFS 深目录 getcwd 损坏
（bash 本身能找到）；本条是 **PATH 里根本没有 bash**——发生在脚本最
早期、与工作目录无关。

## 解法

启动 runner 前**显式补 PATH**：

```sh
ssh <device> 'export PATH=/data/service/hnp/bin:$PATH; \
  sh $HOME/ohos-users/codex/<job>/run-conan-heavy.sh'
```

单包排队/锁机制不受影响。

## 验证

tinymembench-0.4-20260929：r1 无 PATH 前缀 → KC fail；r2 起带
`export PATH=/data/service/hnp/bin:$PATH` → KC pass，后续进入
conan create。r6 全绿（G0/L0/L1/L4/L5 pass，100%）。
