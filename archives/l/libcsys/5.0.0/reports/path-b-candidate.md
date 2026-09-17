# libcsys 5.0.0 路径 B 申报材料（知识库扩展）

> 本材料按仓库既有路径 B 先例（`archives/a/acf-lib-lua5.1/0.11.1/reports/path-b-knowledge.md`、
> `archives/a/acr/2.2.6/reports/path-b-candidate.md`）的形态撰写。
> **最终路径 B 资格与分值以评审委员会结论为准**，本材料不代表已获认可。

## 1. 申报边界

- 任务：`libcsys/5.0.0`
- 分支：`feat/libcsys-5.0.0` → `main`
- 关联 PR：`#9868`
- 关联 Issue：`#3015`（知识库扩展申请已提交：https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3015）
- 上游标签：`v5.0.0`
- 上游源码 SHA-256：`8ba5ddcdcf6162a0db229f2b95312784a30760f09e919960fedb5fd9fe7f9cb9`
- **申请类型：路径 A（基础适配）+ 路径 B 候选（知识库扩展）**
- 不与路径 A 编译分重复申报；不同时申报路径 C（高难度挑战）
- libcsys 体量小（3.1k LOC、Qt6 CMake 一次通过），**不申报"困难库适配分析报告"**——
  难度不在构建，而在上游运行期缺陷与 procfs 解析鲁棒性，故按"知识库扩展"形态申报

## 2. 申请路径 B 的理由

上游 5.0.0 在 HarmonyOS/OHOS 上存在 **4 处运行期缺陷**，其共同特征是
**"编译通过、测试通过、却随时可能崩溃"**，且第 4 处**只在特定 CI worker 上复现**。
单纯"让它编译通过"的最小适配（路径 A）无法覆盖这些缺陷，而它们背后的模式
**可跨库复用**：任何按固定行数/固定字段索引解析 `/proc`、`/sys` 派生文本，
或把"桌面服务存在"当成前提的 C/C++ 库，都会踩同一类坑。

本申报的贡献不是"给 libcsys 打一个只对它生效的补丁"，而是：

1. **提炼出 4 类可复用缺陷模式及判定方法**（写入 `knowledge/drafts/DRAFT-9001-*.{kv,md}`）；
2. **给出"环境相关崩溃"的取证方法**——逐字复刻旧/新解析逻辑 + 构造边界输入，
   让"本地不复现、远端随机红"的缺陷变成可复现证据（`reports/networkinfo-probe.*`）；
3. **把 4 处缺陷整理为可提交上游的通用修复**（见 `reports/upstream-contribution.md`；
   修复中不含任何 `__OHOS__` 平台宏，对上游任意平台均成立）。

## 3. 知识库查重与新增价值

- 新增草稿：`knowledge/drafts/DRAFT-9001-libcsys-5.0.0-ohos-runtime-crashes.kv` / `.md`
- 拟提升编号：由知识库主编确认（草稿不预占正式 E 编号）
- 条目主题：**Qt6 库在 OHOS 上编过但运行期 SIGSEGV：procfs 派生数据无边界检查、
  容器析构条件写反、API 返回值语义误用（四类）**
- 查重关键词：`cpu MHz`、`cpuinfo`、`gethostname`、`removeFirst`、`providers.empty`、
  `UPower`、`logind`、`/proc/net/dev`、`QList::at index out of range`
- **查重实测**（对 `knowledge/graph/*.kv` 全量 540 条逐词检索）：

| 关键词 | 现有条目命中数 |
|---|---:|
| `cpu MHz` / `cpuinfo` | 0 |
| `gethostname` | 0 |
| `removeFirst` | 0 |
| `providers.empty` | 0 |
| `UPower` / `logind` | 0 |
| `procfs` | 1 |

- `procfs` 唯一命中为 **E380**（"Bind a validated memory budget when target CMake
  cannot parse procfs"），主题是 *CMake 在目标 procfs 格式不可识别时绑定内存预算*；
  本条目讲的是 *解析 procfs 文本时按固定行数/字段索引导致的 UB 崩溃*，主题不同但仍
  涉及 procfs，故在草稿中标为相邻条目供主编判重。
- 工具预审：`python3 scripts/ohc-run.py draft-review DRAFT-9001-... --json`
  → `verdict: create`，最高相似度 **0.07**（阈值 0.30），全部候选 `signature_overlap: 0.0`、
  `keyword_jaccard: 0.0` → **确属知识库空白区**

## 4. 四类缺陷与可复用规则

| # | 缺陷（文件） | 根因 | 可复用规则 | 证据 |
|---|---|---|---|---|
| 1 | `InfoManager::update()` 空表越界 | OHOS `/proc/cpuinfo` 无 `cpu MHz` 行 → 频率列表为空，代码按核数下标 `xFrequencies[i]` 读取（release 下 `Q_ASSERT` 被编译掉） | 按 procfs 字段填充的列表，读取端必须越界安全（`.value(i, default)`）或先判 size | 实测 `grep -c "cpu MHz" /proc/cpuinfo` = 0；修复前 `update()` 段错误 EXIT=139 |
| 2 | `Power::~Power()` 析构条件写反 | `while (providers.empty())` 内调用 `takeFirst()` —— 正确应为 `!providers.empty()`；无 logind/ConsoleKit 时 providers 为空 → 空表 `takeFirst()` | 容器析构循环条件必须统一为 `while (!c.empty())`；依赖 D-Bus 提供者的析构器必须能安全遍历空容器 | 修复前"main 跑完、退出瞬间 EXIT=139" |
| 3 | `SystemInfo::getHostname()` 恒返回空串 | `gethostname()` 成功返回 0（非长度），代码把 0 当长度传给 `QString::fromLatin1(buf, size)`；且缓冲区未初始化、堆泄漏 | 不得把系统调用返回值当长度/大小；读取需 strlen 语义且缓冲区零初始化 | 修复前恒为空串；修复后实测返回 `localhost` |
| 4 | `NetworkInfo::getIOBytes()` 空表/短行越界 | 三次无条件 `data.removeFirst()` 删表头 + 无保护 `bytes.at(1)`/`at(9)`；`/proc/net/dev` 不可读时 `readListFromFile()` 返回空表 → 空表 `removeFirst()` 即 UB | 解析 procfs 文本永不按固定行数删除、永不无保护下标：用"跳过不匹配行 + 判 size" | 见 §5；**该缺陷是远端 CI 实测崩溃，本地不复现** |

修复位置：`patches/0001-fix-runtime-crashes.patch`（#1/#2/#3）、
`patches/0002-fix-networkinfo-oob.patch`（#4）。**两个补丁均不含平台宏**
（已通过 preflight PF5 平台宏闸），对上游任意平台成立。

### 上游版本核验（确认非"陈旧修复"）

4 处缺陷在**上游最新 5.0.1 中全部保留**：`csys/infomanager.cpp`、`csys/power.cpp`、
`csys/systeminfo.cpp`、`csys/networkinfo.cpp` 在 v5.0.0 与 v5.0.1 之间**逐字节相同**
（`diff -q` 逐个比对，四个文件均"完全相同"；官方归档 sha256：v5.0.0 `8ba5ddcd…`、
v5.0.1 `e94d996c…`）。缺陷 #1/#2/#4 会硬崩溃，且 #1/#2 对**任意平台**成立
（容器、无 `cpu MHz` 字段、无 logind 的环境），并非 OHOS 专有 —— 具备上游贡献价值，
材料见 `reports/upstream-contribution.md`。

## 5. 环境相关崩溃的取证（本申报的方法论增量）

第 4 类缺陷的价值在于它证明了 **"本地通过 ≠ 远端通过"**：同一份代码在
CI worker **CI-026 上 CI 通过**，在 **CI-007 上 `Signal 11 (core dumped)`**
（`Error 139 while executing`），前 28 条断言全部通过后崩溃。

为了让这类缺陷可复现、可评审，归档内提供了**逐字复刻旧/新解析逻辑**的探针
（`reports/networkinfo-probe.cpp`，不触碰真实 `/proc/net/dev`）与 4 组构造输入：

| 输入（`reports/networkinfo-probe-*.txt`） | 上游逻辑 | 修复后 |
|---|---|---|
| `case1_empty`（0 字节，模拟 `/proc/net/dev` 不可读） | rc=134 `ASSERT: "!isEmpty()"` qlist.h:883 | rc=0 `rx=0 tx=0` |
| `case2_headers_only`（仅两行表头，netns 内无网卡） | rc=134 同上 | rc=0 `rx=0 tx=0` |
| `case3_short_row`（表头 + 正常行 + 短行 `eth1: 5`） | rc=134 `ASSERT failure in QList::at: "index out of range"` qlist.h:513 | rc=0 `rx=100 tx=200` |
| `case4_normal`（真实 `/proc/net/dev`，13 网卡） | rc=0，但 `rx=723411165`（**漏统计首个网卡 `lo`**） | rc=0 `rx=964492761`（13 网卡全计入） |

原始输出见 `reports/networkinfo-probe-evidence.txt`。

## 6. 可复用产出清单

| 产出 | 位置 | 复用价值 |
|---|---|---|
| 知识草稿（4 类根因 + 5 条 forbid 模式 + 验证命令） | `knowledge/drafts/DRAFT-9001-*.{kv,md}` | 同类 Qt6/procfs 库直接命中并照方修复 |
| 环境相关崩溃探针（源码 + 4 组输入 + 原始输出） | `reports/networkinfo-probe.*` | 任何"按固定行数/字段解析 procfs"的库可套用同法取证 |
| 上游通用修复（4 处，无平台宏） | `patches/0001-*.patch`、`patches/0002-*.patch` | 可直接提交上游（见 `reports/upstream-contribution.md`） |
| 消费者测试基线（上游 0 用例 → 41 条断言） | `test_package/test_libcsys.cpp` | 12 类公开 API 的断言可作同类系统信息库的测试起点 |

## 7. 证据材料

| 项目 | 内容 |
|---|---|
| 原始失败 | ① `InfoManager::update()` 段错误 EXIT=139；② `Power` 析构段错误 EXIT=139；③ `getHostname()` 恒空串；④ 远端 CI `Signal 11` → `Error 139`（CI-007） |
| 修复方案 | `patches/0001-fix-runtime-crashes.patch`、`patches/0002-fix-networkinfo-oob.patch`；当前提交见关联 PR 最终 HEAD |
| 构建验证 | Conan 2.29.1；`conan create` 退出码 0；profile `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15 / libc++）；两个补丁均 `Apply patch` 成功 |
| 上游测试 | **0/0（上游未提供任何自动化测试）**——清点命令与原始输出见 `notes.md` R51 申报表与 `test_package/MANIFEST.yml`，未写成 100% |
| 消费者验证 | 对 Conan 产出的 `libcsys.so` 执行 **41 项新增断言，41/41 PASS**（`assertions=41 failures=0`，二进制退出码 0） |
| 本地 CI 模拟 | `ci/conan/build_and_test.sh`（PR diff 模式）：`L0/L1/L4/L5=pass`、`JC/KC=pass`、`Pass rate 100.0% (1/1)`，含 L1e 破坏性反向验证 |
| 独立审查 | W4 独立子任务审计 `reports/audit-result.json` → `verdict: pass`，P0/P1 = 0（审计方自行重下源码复核 sha256） |
| 当前 CI | 关联 PR 已触发官方 CI；最新结果以 PR 页面为准（历史多轮因 CI worker 缺 `libz.so` 导致 `git` 无法启动而失败，属基建故障，已在 PR 讨论区留证） |

详细测试范围与边界见 `reports/test-report.md`。

## 8. 其他说明与明确边界

- 本次只申报"路径 A + 路径 B 候选"；**不申报路径 C**。
- **未删除、未修改上游任何测试用例**（上游本无测试）；41 项断言为全新补写，单独统计。
- **未修改上游源码以"绕过"缺陷**：4 处均为根因修复，且修复方案对上游通用。
- 边界（未写成已验证的部分）：
  - 真实 OHOS 桌面会话（UPower/UDisks2/logind 实际存在）下的行为未验证——本次只验证了
    "服务缺失时优雅降级、不崩溃"；
  - `NetworkInfo` 修复的**远端 CI 复核尚未取得一次成功运行**（worker 基建故障所致），
    当前依据为本地 `conan create` 41/41 + 探针证据；
  - 上游是否接受这些修复，取决于上游维护者（材料已备，见 `reports/upstream-contribution.md`）。

## 9. 需要官方确认的问题

1. 是否认可"4 类 procfs/析构/返回值缺陷模式 + 环境相关崩溃取证方法"为路径 B（贡献创新）评审对象？
2. 是否认可 `DRAFT-9001` 作为同类 Qt6 / procfs 解析库适配的知识库新增条目？
3. 是否允许在 PR 合并、上游接受修复后，由知识库主编确认该条目的最终编号与正文位置？
