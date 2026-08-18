【申请人账号】2301_80739235

【队伍名称】天天开心

【申请日期】2026/08/18

【库名称】pcre2 10.47

## 关联 PR

PR：!5661

PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/5661

分支信息：2301_80739235:feat/pcre2-10.47 → OpenHarmonyPCDeveloper:main

当前提交：89569e4e0774f39cca827f22b2f16a79115acb9e（E330 所述技术修复快照；路径 B 文档提交以 PR 当前 HEAD 回读）

PR 状态：开放中

## 申请路径 B 的理由

本 PR 在完成路径 A 基础适配的同时，解决了一类可跨 Autotools 项目复用的
OpenHarmony/HMDFS 测试执行问题：同一个 Automake 测试清单同时包含无扩展名
shell 驱动和真实 ELF 测试时，不能用统一 shell 或 chmod 伪造通过。E330 提供
干净工作目录能力探测、`CONFIG_SHELL`/`SHELL` 的 post-`conanbuild` 重申、以及
仅对已知 shell 驱动启用的 `LOG_COMPILER` 调度，保留直接 ELF 的原始执行语义。

**推广价值：**适用于在受限 HMDFS/noexec 源码或构建目录中运行 Automake/Autotools
项目，并能保持上游测试清单、测试类型和通过率的真实性。

## 知识库查重与新增价值

| 查重范围 | 结论 |
| --- | --- |
| `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations` | 当前主线 `7e1a0cd8752838cca8573af6237534f7e9aa63ce` 已有 E087、E228、E232 等相邻条目，但没有完整覆盖 E330 的三段组合 |
| 新增 draft | `knowledge/drafts/E330-draft-2301.kv`、`knowledge/drafts/E330-draft-2301.md` |
| 条目主题 | noexec 工作目录的 shell 能力探测 + Conan 环境重申 + 混合 Automake 测试选择性调度 |
| 查重关键词 | `getcwd`、`CONFIG_SHELL`、`conanbuild`、`LOG_COMPILER`、`RunTest`、`RunGrepTest`、direct ELF |

## 证据材料

| 项目 | 内容 |
| --- | --- |
| 原始失败 | PCRE2 10.47 原生 OpenHarmony 构建中，shell 可执行性与工作目录能力不等价；无扩展名 `RunTest`/`RunGrepTest` 不能与两个 ELF 测试统一解释 |
| 修复方案 | `89569e4e0774f39cca827f22b2f16a79115acb9e` 中的能力探测、shell 环境绑定和选择性 `LOG_COMPILER` 设计 |
| 构建验证 | OpenHarmony PC arm64，W3 runner exit 0；Conan recipe revision、package ID、package revision 均来自结构化 `conan create` 输出 |
| 上游测试 | 4/4 PASS：`pcre2posix_test`、`pcre2_jit_test`、`RunTest`、`RunGrepTest` |
| 消费者验证 | 8/8 PASS，另有 6/6 可重定位元数据检查 |
| 审查证据 | PR #5661 的自动 AI Review 正在生成，当前无 P0/P1 结论；以当前 HEAD 后续回读为准 |
| 当前 CI | PR #5661 已创建，当前 Buildbot 匹配构建尚待回读；不得把旧 SHA 或占位评论当作当前 HEAD 通过 |

## 申请分值

**路径 B 贡献创新：10 分候选**

理由：E330 不是 PCRE2 私有补丁，而是以真实混合测试清单证明的可复用
Autotools/noexec 诊断与执行组合方案。

## 其他说明

- 路径 A + 路径 B 同在 PR #5661；不创建独立知识 Issue/PR。
- 本任务是 GLib 2.88.3、Pango 1.58.2 与 abiword-plugin-collab 3.0.8 依赖链的底层前置，作者和申请人固定为 `2301_80739235`。
- 不申报路径 C；不上传 Conan/CNB 或其他制品仓。

## 需要官方确认的问题

1. 是否认可本 PR 按路径 B（贡献创新，10 分候选）评审？
2. 是否认可 E330 的诊断模式属于可跨 Autotools 项目复用的适配知识？
3. 是否认可同一精确快照的修复、4/4 上游测试、8/8 消费者测试和 W3 证据？
