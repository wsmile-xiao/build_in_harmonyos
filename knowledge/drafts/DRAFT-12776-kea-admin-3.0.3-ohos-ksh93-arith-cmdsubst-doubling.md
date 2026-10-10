# DRAFT-12776 — OHOS /system/bin/sh 算术展开内嵌命令替换翻倍命令名（wait 类超时逻辑即刻失败）

> 状态：草稿（来自 kea-admin 3.0.3 适配，task_id=12776）

## 问题

OHOS 真机 `/system/bin/sh`（Korn 系 shell，banner 自带 tracked alias 汇总——`type date` 显示 "date is an alias for date"）在**算术展开内嵌命令替换**时把命令名翻倍：

```sh
local deadline="$(($(date +%s) + timeout))"   # 实际执行 datedate +%s
```

- `sh -x` 轨迹：`+ datedate +%s`，stderr `datedate: inaccessible or not found`；
- 替换结果按空值处理，算术照常完成 → `deadline=4`；
- 等待逻辑随后 `test 4 -lt "$(date +%s)"` 恒真 → **立即宣告超时**。

实测最小复现（真机）：

| 表达式 | 结果 |
|---|---|
| `d=$(( $(echo 5) + 4 ))` | `echoecho: inaccessible or not found` |
| `d=$(( $(id -u) + 4 ))` | `id: bad uid 20020084` |
| `test 5 -lt "$(date +%s)"` | 正常（RC=0，比较在算术之外） |
| `now=$(date +%s); d=$((now + 4))` | 正常（先提升到变量） |

命中场景：Kea 3.0.3 上游 `dhcp_test_lib.sh.in` 的 `wait_for_file` / `wait_for_process_to_stop`，导致 memfile.init 报 `kea-dhcp4.csv was not created in time`（服务端实际能正常起来，是等待逻辑坏了）。

## 根因

`/system/bin/sh` 在 `$(( ... $(cmd) ... ))` 词法/展开阶段把命令词输出两次（`date`→`datedate`），命令查找失败后替换为空串，算术按 0 继续。仅嵌套形态触发；纯算术、比较在算术外的写法均不受影响。`env -i`、`unalias date`、绕 PATH 均无法规避（翻倍发生在命令查找之前）。

## 方案

把命令替换**先提升到变量**，再做算术：

```sh
local now
now=$(date +%s)
local deadline=$((now + timeout))
```

移植/验证任何要跑上游 shell 套件的包时，全树扫描正则 `\$\(\s*\$\(`（`$((` 内嵌 `$(`），逐处改写。kea-admin 3.0.3 以补丁 0009 落地（`src/lib/testutils/dhcp_test_lib.sh.in` 两处；全树 7 个 `$((` 中仅这 2 处是嵌套形态）。

## 验证

- 真机探针 `arith_probe.sh`：翻倍/坏 uid/提升后正常，全部实证（2026-10-04，HarmonyOS PC）。
- 打补丁后上游 memfile 套件 `memfile.version/init/upgrade` 3/3 OK（12.71 s，--timeout-multiplier 10）。
- kea-admin 3.0.3 官方 conan-verify 全门禁通过（见 reports/conan-verify-report.md）。

## 适用边界

- 一切在 OHOS `/system/bin/sh` 下执行的 shell 脚本/测试套件；纯算术与算术外比较不受影响。
- 上游若把 `$(( $(cmd) ... ))` 写在生产脚本而非测试里（如计算 deadline/预算），同样命中——按同类改写。

## 查重差异

- E275（OHOS shell grep -v + set -e）是退出码问题；DRAFT-13617（NUL 字节丢弃）是命令替换的**字节完整性**问题；DRAFT-13491（toybox 空输出）是命令替换返回空串的语义差异。本条目是**算术展开上下文内命令词被翻倍**的独立词法现象，触发条件、错误签名与修复手法（提升变量）均不同。

## 关联交付

- 本草稿与 `archives/k/kea-admin/3.0.3/**`（补丁 0009）同属一次交付。
- 正式 E 编号由知识库主编审核后分配。
