# 知识库扩展 Issue 提交材料（路径 B）

> 本文件为**待提交的 Issue 正文**，按仓库既有申报形态
> （`archives/a/activity-aware-firefox/*/ISSUE_PATH_B.md`）撰写。
> 申请信息已按申请人提供填齐，可直接提交到知识库扩展 Issue。

## 基本信息

- 【申请人账号】`@akajhsbnz`
- 【队伍名称】`jumping_姜圣帝君`
- 【申请日期】`2026/09/14`
- 【库名称】`libcsys`

## 关联 Issue 与 PR

- Issue：#3015（本申请已提交）
- Issue 链接：https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3015


- PR：#9868
- PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/9868
- 分支信息：`feat/libcsys-5.0.0` → `main`
- 当前提交：以关联 PR 的最新提交为准
- PR 状态：已创建，等待官方 CI 与专家评审

## 申请路径 B 的理由

libcsys 5.0.0 在 HarmonyOS PC 上的适配量很小（Qt6 CMake 项目，3.1k LOC，一次配置通过），
**若仅按"能编译、能链接"交付，本库的价值上限很低**。但实测发现上游存在 4 处运行期缺陷，
其共同特征是 **"编译通过、测试通过、却随时可能崩溃"**，最小适配完全无法覆盖：

1. `InfoManager::update()` —— OHOS `/proc/cpuinfo` 无 `cpu MHz` 行，频率列表为空，
   代码仍按 CPU 核数下标读取，release 构建下 `Q_ASSERT` 被编译掉 → **越界读 → 段错误**；
2. `Power::~Power()` —— 析构循环写成 `while (providers.empty())`（条件写反），
   在无 systemd-logind/ConsoleKit 的环境必然执行到空表 `takeFirst()` → **退出瞬间段错误**；
3. `SystemInfo::getHostname()` —— 把 `gethostname()` 的返回值（成功时为 0）当作字符串长度
   传给 `QString::fromLatin1(buf, size)` → **主机名恒为空串**（且缓冲区未初始化、堆泄漏）；
4. `NetworkInfo::getIOBytes()` —— 对 `/proc/net/dev` 连续三次无条件 `removeFirst()` 删表头，
   并对每行无保护地取 `at(1)`/`at(9)`；文件不可读或行数不足即 UB → **段错误**。

第 4 点是最能说明问题的一处：**同一份代码，在 CI worker CI-026 上 CI 通过，
在 CI-007 上 `Signal 11 (core dumped)`（`Error 139 while executing`）**——
前 28 条断言全部通过后崩溃。也就是说，`/proc/net/dev` 的可读性在 worker 之间不同，
**"本地全绿"根本不能证明"远端会绿"**。这类缺陷若不沉淀，同类库会反复踩、反复用 CI 试错。

因此本申报的增量不是"给 libcsys 打个专用补丁"，而是三件可复用产出：

- **4 类缺陷模式 + 判定方法**（写入知识草稿 DRAFT-9001，含 5 条 forbid 模式与验证命令）；
- **"环境相关崩溃"的取证方法**：逐字复刻旧/新解析逻辑 + 4 组构造边界输入，
  把"本地不复现、远端随机红"的崩溃变成可评审的确定性证据；
- **可提交上游的通用修复**（4 处，均不含平台宏，对任意平台成立）。

## 推后价值

可推广到任何 **按固定行数/固定字段索引解析 `/proc`、`/sys` 派生文本**的 C/C++ 库
（CPU/内存/磁盘/网络信息类：`libgtop`、`psutil` 系 C 实现、系统监控面板后端等），
以及任何 **把"桌面服务（logind/UPower/UDisks2）存在"当成前提**的库的析构与降级路径。
方法论层面，"环境相关崩溃的可复现取证"可复用于所有 worker 间行为不一致的 CI 失败。

## 知识库查重与新增价值

- 新增 draft：`knowledge/drafts/DRAFT-9001-libcsys-5.0.0-ohos-runtime-crashes.kv`
- 配套说明：`knowledge/drafts/DRAFT-9001-libcsys-5.0.0-ohos-runtime-crashes.md`
- 拟提升编号：由知识库主编确认（草稿不预占正式 E 编号）
- 条目主题：Qt6 库在 OHOS 上编过但运行期 SIGSEGV：procfs 派生数据无边界检查、
  容器析构条件写反、API 返回值语义误用（四类）
- 查重关键词：`cpu MHz`、`cpuinfo`、`gethostname`、`removeFirst`、`providers.empty`、
  `UPower`、`logind`、`/proc/net/dev`、`QList::at index out of range`
- 覆盖判断（对 `knowledge/graph/*.kv` 全量 540 条逐词检索）：
  `cpu MHz` / `cpuinfo` / `gethostname` / `removeFirst` / `providers.empty` /
  `UPower` / `logind` 命中数**均为 0**；`procfs` 命中 1 条（**E380**，主题为
  "CMake 在目标 procfs 格式不可识别时绑定内存预算"，与"解析 procfs 文本的越界崩溃"不同题）。
  预审工具 `draft-review` 判定 `verdict: create`，最高相似度 **0.07**（阈值 0.30），
  候选条目 `signature_overlap`/`keyword_jaccard` 均为 0.0 → **属知识库空白区**。

## 证据材料

| 项目 | 内容 |
| --- | --- |
| 原始失败 | ① `InfoManager::update()` 段错误 EXIT=139；② `Power` 析构段错误 EXIT=139；③ `getHostname()` 恒空串；④ 远端 CI `Signal 11` → `Error 139`（worker CI-007，前 28 条断言通过后崩溃） |
| 修复方案 | `patches/0001-fix-runtime-crashes.patch`（3 处）、`patches/0002-fix-networkinfo-oob.patch`（1 处）；均不含 `__OHOS__` 等平台宏；当前提交见关联 PR 最终 HEAD |
| 构建验证 | Conan 2.29.1；`conan create archives/l/libcsys/5.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` 退出码 0；产物 `lib/libcsys.so → libcsys.so.5 → libcsys.so.5.0.0`（实测 `DT_SONAME=libcsys.so.5`）、`include/csys/*.h`、`share/pkgconfig/csys.pc` |
| 上游测试 | `0/0（N/A）`；上游未提供自动化测试套件（`grep -rn "enable_testing\|add_test" CMakeLists.txt meson.build` 无命中、无 tests/ 目录），**没有写成 100%** |
| 消费者验证 | 对 Conan 产出的实际 `libcsys.so` 执行 **41 项新增断言**，`41/41 PASS`（`assertions=41 failures=0`，退出码 0） |
| 根因取证 | `reports/networkinfo-probe.cpp` + 4 组构造输入 + 原始输出 `reports/networkinfo-probe-evidence.txt`：上游逻辑在空文件/仅表头/短行三种输入下 rc=134（`ASSERT: "!isEmpty()"`、`QList::at index out of range`），修复后 rc=0；真实 `/proc/net/dev` 下上游还漏统计首个网卡 `lo` |
| 本地 CI 模拟 | `ci/conan/build_and_test.sh`（PR diff 模式，与真实 CI 同口径）：`L0/L1/L4/L5=pass`、`JC/KC=pass`、`Pass rate 100.0% (1/1)`，含 L1e 破坏性反向验证 |
| 审查证据 | 独立 W4 审计 `reports/audit-result.json` → `verdict: pass`，P0/P1 问题为 0（审计方自行重下上游源码复核 sha256 并核对补丁与上游原文） |
| 当前 CI | PR #9868 已触发官方 CI；历史多轮失败中，**两轮为 CI worker 缺 `libz.so` 导致 `/data/service/hnp/bin/git` 无法启动**（`Error loading shared library libz.so` + `exit 127`，构建卡在 git-clone，属基建故障，非本次代码问题，已在 PR 讨论区留证）；`NetworkInfo` 缺陷修复后的远端复核尚待一次成功运行 |

详细测试范围、执行输出和边界见
`archives/l/libcsys/5.0.0/reports/test-report.md`，申报全貌见
`archives/l/libcsys/5.0.0/reports/path-b-candidate.md`。

## 申请分值

- 申请按**路径 B（贡献创新）**评审；**不自行申报具体分值**，以官方审核结论为准。
- 不与路径 A 编译分重复申报，不同时申报路径 C。

## 其他说明

- 本次只申报"路径 A（基础适配）+ 路径 B 候选（知识库扩展）"，**不申报路径 C**。
- **未删除或修改上游任何测试用例**（上游本无自动化测试）；41 项断言为全新补写，单独统计。
- **未用"绕过缺陷"的方式换取构建通过**：4 处均为根因修复（越界安全访问、修正析构条件、
  修正返回值语义、procfs 宽容解析），删除的只有"无条件 removeFirst 删表头"这一错误做法。
- 明确边界（未写成已验证）：
  1. 真实 OHOS 桌面会话（UPower/UDisks2/logind 实际在位）下的功能未验证，本次只验证
     "服务缺失时优雅降级、不崩溃"；
  2. `NetworkInfo` 修复的远端 CI 复核尚未取得一次成功运行（worker 基建故障所致），
     现有依据为本地 `conan create` 41/41 与探针证据；
  3. 上游是否接受这些修复属上游维护者决定（材料已备）。
- 已备好上游贡献材料：`archives/l/libcsys/5.0.0/reports/upstream-contribution.md`
  （含可直接提交上游的 Issue 正文与 4 处修复的 diff）。

## 需要官方确认的问题

1. 是否认可"4 类 procfs/析构/返回值缺陷模式 + 环境相关崩溃取证方法"为路径 B（贡献创新）评审？
2. 是否认可 `DRAFT-9001` 作为同类 Qt6 / procfs 解析库适配的知识库新增条目？
3. 是否允许修复、验证证据和 PR 合并后，由知识库主编确认该条目的最终编号与正文位置？
