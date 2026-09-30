**【申请人账号】** sawakage
**【队伍名称】** 中国矿业大学鸿晕当头
**【申请日期】** 2026/09/17
**【库名称】** librest 0.10.2

## 关联 PR

PR：!10543

PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/10543

分支信息：feat/librest-0.10.2 -> main

当前状态：open

当前路径：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C 候选

## 申请事项

本 Issue 请求评审委员会确认 librest 0.10.2 是否纳入路径 C 高难度挑战候选清单，不直接申请路径 C 分值。若证据不足，代码仍按路径 A + 路径 B 继续评审。该申请绑定唯一的 librest/0.10.2 适配候选和 feat/librest-0.10.2 分支。

## 高难度分析

1. **跨主机 OHOS 工具链边界（HD2_PRIVATE_TOOLCHAIN）**

判定项文字：私有编译工具链，现有知识库无法直接适配。当前 Windows 主机使用 Conan/Meson 交叉编译 OHOS armv8。Conan recipe 需要任务私有的 pkg-config、clang 工具链、GLib 生成工具和共享库别名物化；这些闭包必须逐项绑定到当前候选和 W3 输入，常规单机 Linux 构建不能证明目标可执行。

2. **递归依赖与目标闭包（HD4_LARGE_DEPENDENCY_TEST_COST）**

判定项文字：依赖链庞大、全量测试校验成本极高。librest 运行时闭包跨越 glib、libsoup3、json-glib、libxml2、libffi 和 pcre2，W3 还需签名并回读 22 个 ELF。依赖版本、SONAME、签名、消费者和释放后的进程清零必须在同一 run 中保持一致。

3. **全量测试的确定性边界**

上游 Meson 清单包含 10 项，其中 Flickr 会访问外部 HTTPS 服务。原始公网端点超时不能计为 PASS；本轮在任务私有 host 源副本中使用 loopback fixture，保留测试注册、请求参数和断言，W3 目标 payload 未包含该 fixture。

## 已完成的证据材料

- 前一候选 Conan graph/install r047：`error=null`、旧 `glib/2.84.0.1` 节点数为 0，install RC=0；Buildbot 旧失败 `#50040` 对应全局 `buildid=57261`，根因已由根 recipe 的 `glib/2.84.0.1.1` force 统一 json-glib 侧版本。
- 当前候选 W3 run-029：`launch_count=1`、`consumer 1/1 PASS`、22 个 ELF 已在 PREPARED 阶段签名回读、`RESULT_FROZEN=PASS`、release/postrelease `ROOT_STATE=ABSENT`、`PROCESS_MATCH_COUNT=0`、完整链 `receipts=10`；terminal receipt SHA-256 为 `e407930cb8e51bc798071533badb99c7a547c3bbd05394464ff35a339fd68b53`。run-022 至 run-028 仅保留为不可复用历史。
- 旧候选 `graph-librest-r050.json` / `install-r050.log` 在任务缓存上 RC=0，但 graph 仍包含 `glib2/2.88.0`，并在平台 CI #50072 的 glib2 依赖测试中出现 2 个 timeout 和 1 个 abort；随后 r055-r060 暴露 direct metadata、GLib/GObject linker 闭包和并发回写漂移。当前 r074 已移除 glib2 direct requirement，保留真实 glib/libffi/pcre2 provider，并把 Brotli 间接运行时纳入目标 ELF `NEEDED` 闭包，完成本地交叉包与 W3 run-029。
- 上游 native host Meson 测试：10/10 PASS，skipped=0，timeout=0；原始日志和 fixture 请求日志均已哈希绑定。
- 新知识草稿：`knowledge/drafts/E605-draft-1146.kv` 与同 stem Markdown。
- 四项重判：`reports/hd-reassessment.json`，HD2 与 HD4 命中，HD1 与 HD3 否定。

## 当前状态与边界

当前 Issue 状态：open（创建后保持开启）。PR #10543 已绑定 `feat/librest-0.10.2`；W3 绑定的代码提交 `d8eba714122fdc62207e5df923ace5eccb103e89`、tree `5024b77bc2f96525c52ed1664cd84f133240bb75` 已包含 recipe 与知识草稿修复，W3 run-029 已通过并释放设备；其后的正文/证据文档提交不改变 recipe 或目标 payload。本 Issue 只请求路径 C 候选确认，不宣称已满足路径 C 分值；平台 CI 必须在最终 PR HEAD 上真实 PASS，最新 AI Review 不得有真实未修复问题后才提审。

## 建议验收项

1. 在同一当前 HEAD 上完成平台 CI 和最新 AI Review，并回读 PR 源/目标分支、完整 HEAD 与 Issue 双向关联；Pre-PR 合同当前本地回读为 PASS。
2. 保持上游 10/10、HarmonyOS PC 特有测试 1/1、W3 目标闭包和 release/postrelease 证据相互独立，不以 host fixture 代替目标执行。
3. 复核 HD2/HD4 的工具链、依赖闭包和确定性测试边界，最终以评审委员会结论为准。

## 申请边界

| 路径 | 分值 | 说明 |
|------|------|------|
| 路径 A | 1 分候选 | Conan 构建、安装包消费者与 W3 目标验证已完成 |
| 路径 B | 10 分候选 | E605 提炼跨主机测试执行和网络 fixture 的通用边界 |
| 路径 C | 仅申请候选确认 | 不直接声明分值 |
| 其他 | 不单独申报 | 平台 CI/Review/提审按后续门禁执行 |

*最终以评审委员会审核结果为准。*

## 需要评审委员会确认的问题

1. 是否认可该库作为路径 C 高难度挑战候选。
2. 路径 C 的最低验收证据是什么。
3. 是否接受外部 Flickr endpoint 仅在 host 测试副本使用 task-private fixture 的边界。
4. 若当前暂不纳入路径 C，是否认可本 PR 先按路径 A + 路径 B 继续评审。
