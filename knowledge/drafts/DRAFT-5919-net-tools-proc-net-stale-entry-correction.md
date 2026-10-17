# E434 草稿 — 知识库过时条目纠错机制：/proc/net 权限边界实证修订（E6400 实例）

## 可复现症状与稳定错误签名

- 矛盾签名：知识库旧条目 E6400 记"/proc/net 其余项可读（仅 /proc/crypto 隐藏）"，
  而 2026-09-26 真机实测 `/proc/net` 文件内容读取 **12/12 全线 EACCES**：
  `head -c 40 /proc/net/tcp` → Permission denied（route/arp/dev/tcp/udp/unix/
  sockstat/stat/wireless/protocols/netstat/if_inet6 逐一实测同拒）。
- 工具症状：`netstat -rn`/`route -n` → `/proc/net/route: Permission denied`
  （rc=1）；`arp -n` → `/proc/net/arp: Permission denied`（rc=255）；
  `ifconfig -a` → `Warning: cannot open /proc/net/dev (Permission denied).
  Limited output.` + 仍列出真实接口 lo/wlan0（降级路径）。

## 根因与最小复现

- 根因：**知识库条目随平台演进过时**。E6400 记录的是旧版 OHOS 的 /proc/net
  权限形态（"其余项可读"）；当前 HarmonyOS PC 沙箱已把 /proc/net 文件内容
  全线收紧为仅特权 uid 可读（目录列举 ls 仍可读，70+ 条目可见）。Linux/Android
  上这些文件世界可读，普通用户 `netstat -rn` 合法——差异在平台权限模型。
- 旧条目危害：后续网络工具适配若按"其余项可读"写断言/设计降级逻辑，会得到
  错误预期——真机直接 FAIL，或误判为配方缺陷。
- 最小复现：`head -c 40 /proc/net/tcp` → Permission denied；`ls /proc/net/` →
  正常；`hostname` → `localhost`（与 /proc/net 无关的查询不受影响）。
- 触发实例：net-tools 2.1 消费者测试（conan create G2，2026-09-26，华为 PC
  真机，Conan 2.29.1，uid 20020084）：36 断言首轮 33 passed / 3 failed，
  3 个失败全部是上述权限拒绝，其余 T1 ELF/T2 ifconfig+hostname/T3 7 工具/
  T4 --version 全过。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 断言一律按硬 FAIL（初版 test.sh） | 真机 G2 FAIL——把平台行为误判为配方缺陷 |
| 直接改写 E6400 条目 | 否决——不实证就改旧条目可能引入新错误（forbid_1），且丢失历史轨迹 |
| 对 Permission denied 全量放行 | 否决——掩盖真缺陷（forbid_1） |
| 新条目 + 修订标注 + restricted-assert（采纳） | E434 记录最新边界与修订证据，E6400 在新条目 causes 标注修订；test.sh 按严格纪律做平台受限断言 |

## 最终方案、输入输出与真实验证

- 处理：①逐文件实证权限矩阵（12/12 EACCES + 目录列举可读）；②新条目 E434
  记录最新事实 + 修订证据（日期/设备/uid/矩阵）；③旧条目 E6400 在 causes
  段标注修订，不删除；④test.sh 新增 `restrict()` 计数——T2 三处断言在 FAIL
  分支前增加 Permission denied 判定，命中记 RESTRICTED；汇总行
  `N passed, R restricted, S skipped, F failed`；FAIL>0 仍 exit 1；
  PASS=0 且 RESTRICTED=0 仍 exit 1。
- 输出：`RESTRICTED: netstat -rn 平台受限（OHOS /proc/net/route 权限拒绝）`。
- 真实验证：net-tools 2.1 真机 conan create 复验 **33 passed / 3 restricted /
  0 failed**，conan-verify G0-G4/L1-L5 全绿判定 published
  （archives/n/net-tools/2.1/reports/conan-verify-report.md）。

## 适用范围、反例、解除条件与风险

- 适用：①知识库旧条目与真机现状矛盾的一切场景（尤其平台权限/文件系统行为
  随版本演进类）；②网络状态查询类工具（net-tools 全系读表面、iproute2 的
  route/neigh 查询、ss/lsof 网络面）的消费者测试断言。
- 反例：工具对受限文件 die() 退出（进程无法启动）时不可靠断言放行
  （topline 对 /proc/diskstats 的 E429 情形），必须代码级优雅降级；
  权限拒绝发生在其他文件/路径（非 /proc/net 查询语境）时仍按 FAIL。
- 解除条件：平台未来放开 /proc/net 文件读权限后，受限判定自然不再命中，
  断言回归 rc=0 分支（无补丁依赖）；本条届时成为新的"过时条目"，
  由同一机制再修订——机制本身不失效。
- 风险：restricted 与 fail 边界若放宽过度会掩盖真回归——判定条件必须同时
  限定文件语境与错误签名（见 forbid_1）；修订必须附实证，防止"纠错"引入新错。

## 知识库查重与新增价值

- grep index.tsv：命中 E429（/proc/diskstats 仅 root 可读）、E031（htop /proc
  整体受限）、E303（受限进程文件系统探测）、E6400（被修订条目）、DRAFT-9001
  （libcsys 因 /proc/net/dev 不可读崩溃）。
- 与近亲条目的区隔：E429/E031/E303 是**事实条目**（"某文件受限→降级补丁"），
  本条是**元知识**——"知识库条目本身会随平台演进过时，需要实证修订机制"，
  以 E6400 为完整实例；同时补上近亲条目都没有的**restricted-assert 断言纪律**
  （语境限定 + rc 非零 + 签名匹配 + 真实 PASS 维度兜底 + 四计数汇总）。
- 新增价值：①给出可复用的"旧条目 vs 真机矛盾"处理流程（实证矩阵→新条目+
  修订标注→断言策略），后续任何包发现同类矛盾可照此办理；②/proc/net
  12/12 权限矩阵精确刷新平台边界；③E6400 修订证据归档（不删旧条目，
  causes 引用保留历史轨迹）。
