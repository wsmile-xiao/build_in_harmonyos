**【申请人账号】**2301_80739235

**【队伍名称】**天天开心

**【申请日期】**2026/08/22

**【库名称】**librasterlite2 1.1.0-beta1

## 关联 PR

PR：待创建

PR 链接：待创建

分支信息：feat/librasterlite2-1.1.0-beta1 -> main

当前提交：待提交

PR 状态：尚未创建

## 申请路径 B 的理由

本适配不是一个孤立补丁。目标端完整测试依次暴露了三类可迁移问题：PowerShell 负例可被空字符串参数绑定提前截断、C plain `char` 的目标默认符号性可改变 INT8 API 的整数提升结果，以及 Conan 共享包的链接依赖元数据与消费者运行时库目录传播是两个独立合同。三类问题分别沉淀为 E2157、E2158、E2159 草稿，可推广到跨平台验证器、图像/音频/二进制格式库和 Conan 2 共享库消费者。

**推广价值：可推广到 PowerShell 生产路径负例、使用 plain `char` 表达有符号 8 位数据的 C 库，以及通过 `cpp_info.requires` 暴露共享依赖的 Conan 2 配方。**

## 知识库查重与新增价值

新增 draft：knowledge/drafts/E2157-draft-2301.kv、knowledge/drafts/E2158-draft-2301.kv、knowledge/drafts/E2159-draft-2301.kv，均有同 stem Markdown 文件

拟提升编号：E2157、E2158、E2159（最终编号由知识库主编确认）

条目主题：严格负例参数绑定、plain-char signedness 和 Conan transitive runtime libdirs

查重关键词：AllowEmptyString、plain char、fsigned-char、VirtualRunEnv、runenv_info、libminizip.so.1、LD_LIBRARY_PATH

覆盖判断：current main 的 E298 只覆盖 `VirtualRunEnv + conanrun` 执行，E319 覆盖 Python `PYTHONPATH`，E320 覆盖 `tmpfile()` 能力 fallback；现有条目未完整覆盖上述三类问题。本次查重结论为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`，同时复用 E298、E319 与 E320 的既有边界。

## 证据材料

| 项目 | 内容 |
| --- | --- |
| 原始失败 | 历史诊断：r47 出现 `-120 -> 136`、`-17 -> 239`；r107 消费者加载 `libminizip.so.1` 失败；本地验证矩阵曾被 mandatory empty-string 参数绑定提前截断。R218 未把这些 predecessor 的每个原始结果身份纳入当前审计闭包 |
| 修复方案 | Conan toolchain 统一 `-fsigned-char`；producer `runenv_info` 传播依赖 libdirs；严格负例只在空字符串是合法状态时使用 `AllowEmptyString` 并匹配精确下游诊断 |
| 构建验证 | OpenHarmony PC arm64 真机 r196，root package 强制源码构建，依赖 `--build=never`，runner RC 0 |
| 上游测试 | Automake 71/71 PASS（100%）；另审计 1,379 个嵌入 SQL 场景，它们不重复计入独立测试分母 |
| 消费者验证 | 一个 Conan `test_package` 消费者流程 PASS，内部 14/14 断言；producer `runenv_info` 源码检查与 consumer 自建 libdir 环境共同证明组合闭包，不宣称 producer 单变量验证；14 条断言不申报为 14 个独立测试用例 |
| 审查证据 | 双路独立完整 W4 R218：PASS / NOT_STALE，canonical SHA-256 `37e7760e4d02de7d39943e9423cc7879c1ac9a1512e1c7963180111176ce2d93`，P0/P1/P2/P3=0/0/3/0；P2 均为非运行元数据与证据边界说明，不阻塞 |
| 当前 CI | 尚未创建 PR，因此 Buildbot CI 尚未开始；创建后只接受 exact current-HEAD 的完整成功结果 |

*本任务使用上游 Automake 测试入口，测试规模为 71 个独立入口；测试源码和期望未修改。消费者流程补充公开 API、对象所有权和运行时依赖闭包验证。*

## 申请分值

**路径 B 贡献创新：10 分候选**

理由：三个配对草稿都来自可复现的生产/目标路径问题，给出根因、修复、正负验证和禁止边界，能够跨库与跨版本复用。

*测试框架/工具链验证作为路径 B 证明材料，不重复申报额外分值。最终以官方审核为准。*

## 其他说明

- 本软件 PR 同时完成路径 A 基础适配，并作为 spatialite-gui 的真实前置依赖；Issue/PR 标题按优先级只使用 `【知识库扩展】`。
- 上游版本是官方 `1.1.0-beta1` 预发布版，不是稳定版 `1.1.0`。
- 合并前不执行 `/release`，不从本机上传 Conan/CNB；仅允许合并后平台发布。

## 需要官方确认的问题

1. 是否认可本 PR 按路径 B（贡献创新，10 分候选）评审
2. 是否认可上述三类诊断/组合方案属于可跨库复用的适配知识
3. 是否认可修复与验证证据，并允许草稿在主编审核时确定最终编号
