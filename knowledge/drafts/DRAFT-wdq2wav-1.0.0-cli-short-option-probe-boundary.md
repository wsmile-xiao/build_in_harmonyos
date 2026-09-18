# DRAFT-wdq2wav-1.0.0-cli-short-option-probe-boundary - 通用长选项探针失败时应按上游短选项契约验证 CLI

wdq2wav 1.0.0 只通过 `getopt` 注册 `-h`、`-r` 等短选项，通用 L2 探针却尝试 `--help/--version`。因此，L2 的长选项探针 skip 只表示探针能力与上游接口不匹配；应使用已安装二进制真实支持的 `-h` 做消费者验证，不能据此宣称构建或功能失败。

## 身份与当前结论

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-wdq2wav-1.0.0-cli-short-option-probe-boundary` |
| 配套结构化文件 | `knowledge/drafts/DRAFT-wdq2wav-1.0.0-cli-short-option-probe-boundary.kv` |
| 当前状态 | 已有验证证据待审 |
| 建议去向 | 补充既有模式 E570 |
| 实际贡献者 | Windrel（原实现与本次知识提炼） |
| 来源任务/PR | [PR #3798](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/3798)；Issue #1715 |
| 提取方式 | 已有普通 PR 升级 |
| 本次交付 PR | 原位升级为同一 PR #3798 |
| 包及配方版本 | wdq2wav / 1.0.0 |
| 上游版本与源码 | 1.0.0+dfsg；Debian source tarball；SHA256 `6c99ee94e8e697f2cf41188c952f7ab90cba2d7deb04fd7dad24918fa9f0139d` |
| 知识来源提交 | `861e7b226bd6f43386f10b3fe29ee95d5f49f58a` |
| 被验证提交 | `861e7b226bd6f43386f10b3fe29ee95d5f49f58a` |
| 最后更新 | 2026-09-16 |

本草稿验证到：OHOS 构建产物可由 `test_package` 执行 `wdq2wav -h`，退出码为 0，输出包含 `usage:`、`wdq-file` 和 `wav-file`；同次验证的通用 L2 长选项探针为非阻塞 skip。仍未证明：真实 WinDAQ 到 WAV 的转换路径、音频播放路径，以及为 wdq2wav 新增 GNU 长选项是否符合上游维护策略。

## 从普通 PR 提取的依据

原 PR 标题、状态与提取基线：`【知识库扩展】feat(wdq2wav): 1.0.0 编译适配`，open，PR #3798，基线 HEAD `861e7b226bd6f43386f10b3fe29ee95d5f49f58a`。

| 原 PR 事实 | 具体位置与版本 | 提炼出的可复用机制 | 本次补充 |
|---|---|---|---|
| 通用 L2 报告 `version/help failed`，但构建和 L1 均通过 | `archives/w/wdq2wav/1.0.0/notes.md`；CI #24853 | 通用长选项探针是能力探针，不等于实际支持的 CLI 契约 | 成对知识草稿与证据报告 |
| 消费者测试运行 `wdq2wav -h` 并检查退出码及三个输出标志 | `test_package/test.cpp`，HEAD `861e7b2` | 使用上游承诺的选项验证安装产物，避免用不支持的 GNU 长选项制造假失败 | 明确反例和适用边界 |
| 上游 `getopt` 选项串为 `rqvzmndph`，`case 'h'` 返回 0 | 上游 tarball SHA256 `6c99...139d` 的 `wdq2wav.cpp` | 失败来自探针与接口不匹配，不是 OHOS 平台或交叉编译产物故障 | 本次提炼时补做静态源码核对 |

原 PR 已有的贡献：Conan 配方、Makefile 可移植性补丁、包元数据、消费者测试，以及 OHOS 构建验证。

本次提炼新增的贡献：将 L2 skip 与消费者测试之间的边界整理为可复用知识，并与 E570 去重。
历史记录与本次实验的区分：CI #24853 和真机摘要来自原 PR；上游源码选项核对与知识去重在本次提炼时完成，未虚构历史失败。

升级依据：该案例为 E570 增加一个重要边界。E570 推荐在交付契约要求 GNU 长选项时补 `getopt_long`；本案例证明，当项目只需保持上游接口且通用探针非阻塞时，应优先验证真实支持的短选项，不能为了探针通过而扩大接口。

## 1. 触发条件与可辨认现象

| 条件 | 本次实际值 | 为什么影响结论 |
|---|---|---|
| 目标系统、架构、运行域 | OHOS，PR 的单包构建环境 | 消费者测试实际运行的是目标包内 CLI |
| 编译器及构建工具 | clang++、Makefile、Conan、CMake test_package | 构建与运行探针分层，L2 skip 不推翻 L0/L1 结果 |
| 关键依赖及版本 | 无外部三方依赖 | 排除第三方运行依赖缺失造成启动失败 |
| 文件系统、路径、权限或硬件 | `VirtualRunEnv` 提供包内 `bin` 路径；无音频硬件要求 | `-h` 不触发文件转换或播放路径 |
| 最小输入与前置步骤 | 安装 wdq2wav 1.0.0 后运行 `wdq2wav -h` | 验证 CLI 启动及帮助契约，不代表转换功能 |

首次可定位的现象来自原 PR 验证摘要：

```text
L2_RESULT=skip: wdq2wav version/help failed
wdq2wav CLI help test: OK
```

建议错误签名：`L2_RESULT=skip: wdq2wav version/help failed`。该签名命中本次 L2 记录；正常消费者输出 `wdq2wav CLI help test: OK` 不命中。

## 2. 根因与排除项

上游 `wdq2wav.cpp` 使用 `getopt(argc, argv, "rqvzmndph")`，`case 'h'` 打印帮助并返回 0，`case 'r'` 提供版本信息；没有注册 `--help` 或 `--version`。通用 L2 探针使用长选项，因而得到 skip。相同安装产物经 `-h` 消费者测试成功，说明该记录不能归因为二进制未安装、无法启动或 OHOS 不兼容。

| 可能原因 | 检查方法与证据 | 结论 |
|---|---|---|
| 交叉编译产物无法运行 | CI #24853 的 Conan test_package 运行安装产物 | 已排除 |
| 包内 PATH 未生效 | `VirtualRunEnv` 下 `popen("wdq2wav -h")` 成功 | 已排除 |
| 上游同时承诺 GNU 长选项 | 核对固定 SHA256 上游源码及 man page | 已排除；文档只列短选项 |
| 实际转换功能正确 | 没有合法 WinDAQ fixture 与 WAV 内容断言 | 仍未验证 |

## 3. 最小修复与选择条件

1. 不修改上游 CLI，仅在 `test_package` 中运行上游明确支持的 `-h`。
2. 同时断言退出码为 0，以及 `usage:`、`wdq-file`、`wav-file` 三个辨别性文本，证明运行的是预期安装产物。
3. 将通用长选项探针记为能力 skip；只有下游交付契约明确要求 `--help/--version` 时，才评估 E570 的 `getopt_long` 方案。

实际实现位于 `archives/w/wdq2wav/1.0.0/test_package/test.cpp`，知识来源提交为 `861e7b226bd6f43386f10b3fe29ee95d5f49f58a`。

```sh
wdq2wav -h 2>&1 | grep -q 'usage:'
```

该命令只验证 CLI 帮助契约。未验证回退方案；真实转换验证需要合法 WinDAQ fixture 和 WAV 内容断言。

## 4. 验证矩阵与证据绑定

| 证据 ID | 类型 | 提交、环境与输入 | 命令/测试入口 | 实际结果 | 日志/附件、定位与哈希 |
|---|---|---|---|---|---|
| EVID-01 | static | 上游 1.0.0+dfsg，SHA256 `6c99...139d` | 检查 tar 清单、`wdq2wav.cpp` 和 man page | 仅发现 5 个源码/文档文件；选项解析只注册短选项，`-h` 返回 0 | `archives/w/wdq2wav/1.0.0/reports/knowledge-evidence.md` |
| EVID-02 | target-executed | HEAD `861e7b2`，OHOS 单包验证 | Conan `test_package` 执行 `test_wdq2wav` | 通过，输出 `wdq2wav CLI help test: OK` | CI #24853；PR `notes.md` |
| EVID-03 | historical | 同一 HEAD 的 CI 门禁 | `/rebuild` 触发 CI | L0、L1 和 Conan test_package 通过；L2 长选项探针非阻塞 skip | [CI #24853](https://ohpcd.atomgit.com/ci?id=24853) |

### 被验证文件范围

| 文件或输入 | 验证时版本/哈希 | 与当前提交的关系 |
|---|---|---|
| 配方、补丁、manifest、notes | Git blob 见证据报告 | 与被验证提交相同 |
| `test_package` 四个文件 | Git blob 见证据报告 | 与被验证提交相同 |
| 上游源码 | SHA256 `6c99ee94e8e697f2cf41188c952f7ab90cba2d7deb04fd7dad24918fa9f0139d` | 与配方固定输入相同 |

被验证提交之后新增软件级 CLI 元数据、知识草稿和证据报告，未改变实现、依赖、补丁或测试输入；当前 HEAD 的文档检查需在提交后重新执行。

### 测试统计

| 测试层与明确范围 | 计数单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 库存依据及未执行原因 |
|---|---|---:|---:|---:|---:|---:|---|
| 上游源码包 | 用例 | 0 | 0 | 0 | 0 | 0 | 固定 SHA256 tarball 仅含 Makefile、两个源码/头文件和两份文档，无测试入口 |
| 已安装包消费者 | 测试程序 | 1 | 1 | 0 | 0 | 0 | `test_package/test.cpp`，CI #24853 通过 |
| 消费者内部检查 | 声明断言 | 4 | 4 | 0 | 0 | 0 | `test_package/MANIFEST.yml` 的 `assertion_count: 4` |
| 通用 L2 CLI 探针 | 探针 | 1 | 0 | 0 | 1 | 0 | 不支持 `--help/--version`，记录为非阻塞能力 skip |

结论的证据等级：`-h` 消费者行为是目标环境实跑；选项表和上游测试库存是固定源码静态核对；真实转换、播放及生成 WAV 内容均未覆盖。

## 5. 适用边界与禁止做法

| 可复用前提 | 已验证范围 | 未验证或不适用范围 |
|---|---|---|
| 上游明确提供可无输入运行的短选项 | wdq2wav 1.0.0 `-h` | 需要交互、硬件或输入文件的命令 |
| 通用长选项探针是非阻塞能力探测 | 本次 L2 skip，L0/L1 仍通过 | 仓库明确把 GNU 长选项列为交付契约的工具 |
| 消费者测试检查退出码和辨别性输出 | 帮助入口与安装产物可执行性 | WinDAQ 解析和 WAV 正确性 |

| 错误做法 | 为什么不成立 | 可观察后果 |
|---|---|---|
| 把 `--help/--version` 失败直接写成构建失败 | 探针调用了上游未承诺的接口 | 与通过的 L0/L1/test_package 证据矛盾 |
| 只为使通用探针通过而修改上游参数解析 | 在没有消费者需求时扩大公开接口，不是最小适配 | 产生不必要补丁与维护负担 |
| 把 `-h` smoke 写成转换功能通过 | 帮助分支不解析 WinDAQ 也不生成 WAV | 夸大实际能力 |

## 6. 与已有知识的关系及增量

| 已核验的条目/草稿/前序 PR | 已有内容 | 本次新增机制、边界或证据 | 建议处理 |
|---|---|---|---|
| E570 | 老 CLI 不支持 `--help/--version` 时，可在交付契约要求 GNU 长选项的前提下补 `getopt_long` | 增加反向选择边界：若长选项仅是非阻塞通用探针且上游短选项契约足够，应验证受支持选项并保留 skip，不应自动补接口 | 补充 |
| DRAFT-ohos-makefile-explicit-toolchain-and-install-vars | 手写 Makefile 的编译器与安装工具边界 | PR 的 Makefile 补丁是该既有模式的应用，不重复申报 | 留作案例 |

检索范围与关键词：`knowledge/drafts`、`knowledge/graph`；检索 `--help`、`--version`、`short option`、`L2`、`Makefile`、`install -o root`、`g++`。命中 E570 和 Makefile 既有草稿，因此本次只申报 E570 的选择边界与 wdq2wav 实证。

本 PR 不是同一任务重提；复用了 E570 的问题分类和 Makefile 既有知识，未把常规 Makefile 适配重复计算为新增知识。

## 7. 来源索引与提交自检

| 材料 | 路径或链接 | 固定版本及角色 |
|---|---|---|
| 上游源码 | Debian `wdq2wav_1.0.0+dfsg.orig.tar.xz` | SHA256 `6c99...139d`，静态契约与测试库存 |
| 修复实现 | `archives/w/wdq2wav/1.0.0/patches/0001-Makefile-use-toolchain-and-portable-install.patch` | `861e7b2`，原适配贡献 |
| 消费者测试 | `archives/w/wdq2wav/1.0.0/test_package/test.cpp` | `861e7b2`，目标环境行为验证 |
| 汇总证据报告 | `archives/w/wdq2wav/1.0.0/reports/knowledge-evidence.md` | 本次新增 |
| 原始验证记录 | [CI #24853](https://ohpcd.atomgit.com/ci?id=24853) | PR 评论与 `notes.md` 摘要 |

- [x] ID、两个文件名和 KV 的 `doc_file` 一致。
- [x] KV 字段均为单行，根因、签名、方案与本文一致。
- [x] 引用的实现路径存在于知识来源提交；新材料进入本次提交范围。
- [x] 包版本、上游版本、PR 标题和测试统计一致。
- [x] 关键结论均有证据，未执行的转换功能已明确标记。
- [x] 已搜索重复材料，并将本候选定位为 E570 补充。
- [x] 已填写普通 PR 来源提取表并区分历史与本次提炼。
- [x] 当前主线中央目录预审已发现并解析草稿；提交后仍需核对远端文件。

最终处理建议：补充既有 E570 的选择边界与实证。

原 PR 升级建议：支持原位升级；需要本次成对草稿和证据报告进入 PR 后再视为 applied。
剩余问题及下一项具体动作：提交材料、运行当前 HEAD 检查，并核对 PR 远端文件与正文。
