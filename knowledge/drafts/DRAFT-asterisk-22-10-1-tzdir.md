**DRAFT-asterisk-22-10-1-tzdir — Asterisk stdtime 通过 TZDIR 注入 HarmonyOS 可访问的 IANA 时区目录**

Asterisk stdtime 原先使用编译期 `TZDIR` 拼接时区文件路径。HarmonyOS runner 的标准 IANA zoneinfo 可能位于不同的可访问目录；补丁增加非空环境变量 `TZDIR` 覆盖，同时保留未设置时的原默认值，并让加载和 watcher 使用同一目录。

**身份与当前结论**

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-asterisk-22-10-1-tzdir` |
| 当前状态 | 有 host/static 证据；目标环境 TZDIR 直接验证仍待补 |
| 建议去向 | 补充既有模式（E315） |
| 实际贡献者 | `gcw_hL6s3dcK`；提交作者 Theresa <ylinzixuan@qq.com> |
| 来源任务/PR | 原 PR [#9563](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/9563) |
| 提取方式 | 已有普通 PR 升级 |
| 本次交付 PR | [#9608](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/9608) |
| 包及配方版本 | `asterisk` / `22.10.1` |
| 上游版本与源码 | `22.10.1`；`https://github.com/asterisk/asterisk/archive/refs/tags/22.10.1.tar.gz`；SHA-256 `373c98f4d4a1b923b42def0aee03f4e36aca9d1c244a8eeda646da8a97f89663` |
| 知识来源提交 | `d0c8db7369c7468a61b11deeadcff01b0fa984d9` |
| 被验证提交 | `d0c8db7369c7468a61b11deeadcff01b0fa984d9` |
| 当前交付代码提交 | `5a6a8e0dd766f416251869b9cb4e6a4bf1b89ab4`（文档补写前当前代码快照；最终 PR HEAD 另行记录） |
| 最后更新 | `2026-09-14` |

本草稿确认运行时目录覆盖的实现机制和默认值回退，并补充 E315 未覆盖的 Asterisk
stdtime watcher 路径边界。当前没有独立的目标环境 TZDIR 直接通过日志；该事实不影响
Conan/HarmonyOS 制品适配主线，但不能宣称 TZDIR 已完成目标环境验证。

**从普通 PR 提取的依据**

原 PR 标题为 `fix(asterisk): 22.10.1 支持 TZDIR 时区目录`，固定 HEAD 为 `d0c8db7369c7468a61b11deeadcff01b0fa984d9`。本次新 PR 将 TZDIR 作为运行时适配保留，补充门禁元数据和知识证据；上游 full-PBX 测试修复不属于本草稿和本 PR 的验收范围。

| 原 PR 事实 | 具体位置与版本 | 提炼出的可复用机制 | 本次补充 |
|---|---|---|---|
| `localtime.c` 的时区加载和 watcher 路径读取运行时 TZDIR | `0015-main-stdtime-tzdir-env.patch`，来源提交 `d0c8db7369` | 数据目录属于部署环境输入，应运行时注入并保留默认回退 | 增加知识草稿和制品适配证据 |
| 官方 CI 在 Conan 构建前失败 | PR #9563，CI #44591，`L0k/L0n` | 当前 CI 没有执行 stdtime，用例结果仍待验证 | 新分支名包含 `asterisk-22.10.1`，并加入软件级 `commands.json` |

**1. 触发条件与可辨认现象**

| 条件 | 本次实际值 | 为什么影响结论 |
|---|---|---|
| 目标系统、架构、运行域 | HarmonyOS/OHOS，aarch64，Asterisk runtime | 设备的 zoneinfo 路径不必等于编译机默认路径 |
| 编译器及构建工具 | Conan 2.x、Autotools；官方 worker 使用 `ohos-aarch64` | 仅提供构建和运行上下文 |
| 关键依赖及版本 | Asterisk `22.10.1` | 补丁定位到该上游版本 |
| 文件系统、路径、权限或硬件 | 标准 IANA zoneinfo 目录由运行环境提供 | 固定 `/usr/share/zoneinfo` 可能不可达 |
| 最小输入与前置步骤 | 设置非空 `TZDIR` 并加载 named timezone | 验证运行时路径和默认回退 |

历史 CI #44591 的失败发生在 L0：

```text
o[fail] L0k: CLI tool detected but commands.json missing (R38)
o[error] L0n: branch name mismatch (R40)
oL0_RESULT=fail: gate failed: commands_json_r38 branch_name_r40
```

建议错误签名：`TZDIR|tzload.*zoneinfo|GMT.*timezone|Cannot.*timezone`。当前日志没有进入 stdtime 运行测试。

**2. 根因与排除项**

编译期 `TZDIR` 不能表达设备部署时的 zoneinfo 位置；路径不可访问时，named timezone 加载会失败或回退到错误的默认行为。`ast_tzdir()` 只覆盖非空环境变量，未设置时仍返回原宏值，因此不改变默认部署。

| 可能原因 | 检查方法与证据 | 结论 |
|---|---|---|
| zoneinfo 数据本身缺失 | 当前 CI 在 L0 停止，没有设备数据证据 | 仍可能，需要真机确认 |
| 代码只改加载、不改 watcher | 对照补丁中的 `tzload`、`add_notify`、`notify_daemon`、`common_startup` | 已检查，四类路径都改用运行时目录 |
| 当前 CI 已执行 timezone 测试 | CI #44591 L0 日志 | 已排除，当前运行未执行 |

**3. 最小修复与选择条件**

1. 增加读取非空 `TZDIR` 的小函数。
2. 将时区加载、默认规则和 watcher 的目录拼接统一切换到该函数。
3. 部署时必须提供真实可访问且包含 IANA zoneinfo 的目录；不应把设备私有路径写入配方。

实际修复来源：[commit `d0c8db7369`](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/commit/d0c8db7369c7468a61b11deeadcff01b0fa984d9)。

```sh
git apply --check --ignore-whitespace archives/a/asterisk/22.10.1/patches/0015-main-stdtime-tzdir-env.patch
```

该命令只验证补丁可应用；未验证回退方案。

**4. 验证矩阵与证据绑定**

| 证据 ID | 类型 | 提交、环境与输入 | 命令/测试入口 | 实际结果 | 日志/附件、定位与哈希 |
|---|---|---|---|---|---|
| EVID-01 | historical | `d0c8db7369`，官方 HarmonyOS worker | 官方 `build_and_test.sh` | L0 失败，未执行 stdtime | PR #9563，CI #44591 |
| EVID-02 | host-executed | `d0c8db7369`，官方源码 tarball SHA-256 如上 | `git apply --check` | 通过 | 本地验证记录；补丁路径如上 |
| EVID-03 | host-executed | 新分支 R38 元数据 | `python -m json.tool archives/a/asterisk/commands.json; git diff --check` | 通过 | 当前新 PR 提交前检查 |
| EVID-04 | target-executed | 当前目标包；远端 `artifacts/type-timeval-correct3-20260914/` | `test execute category /main/stdtime/ name time_tv_to_usec` | 1/1 PASS | `registered.log`、`registered-one.log`、`execute.log`、`results.xml`、`console.log`；仅证明该 stdtime 用例，不证明 TZDIR |

**测试统计**

| 测试层与明确范围 | 计数单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 库存依据及未执行原因 |
|---|---|---:|---:|---:|---:|---:|---|
| Asterisk stdtime/TZDIR 定向范围 | 用例 | 未知 | 未知 | 未知 | 未知 | 未知 | 未保存独立目标环境 TZDIR 日志；SSH 已恢复但仍无直接 TZDIR 证据 |
| 已安装包消费者历史验证 | 断言 | 1 | 1 | 0 | 0 | 0 | 既有 test_package / `asterisk -V` 记录 |
| 修复边界与反例 | 断言 | 2 | 未知 | 未知 | 未知 | 未知 | 未保存独立反例日志；SSH 已恢复但本轮未执行独立反例 |

本草稿不提供上游 full-PBX 测试通过率；TZDIR 直接定向结果仍未知。证据等级为 host/static + historical，不能由其他入口结果推导 TZDIR 通过。

**5. 适用边界与禁止做法**

| 可复用前提 | 已验证范围 | 未验证或不适用范围 |
|---|---|---|
| 运行环境能提供包含目标区域的 IANA zoneinfo 目录 | Asterisk 22.10.1 的 stdtime 路径逻辑静态补丁 | 真机 zoneinfo 内容、权限、watcher 事件和完整套件 |

| 错误做法 | 为什么不成立 | 可观察后果 |
|---|---|---|
| 把设备私有 zoneinfo 路径硬编码、强制 GMT 或跳过时区测试 | 目录属于部署输入，且 GMT 不是 named timezone 的等价实现 | 时区错误或测试覆盖丢失 |

能力缺失、skip、失败和成功必须由真机日志区分；当前只确认旧 CI 的 L0 门禁失败和本轮 full-run 卡住，不能把 TZDIR 未验证写成失败或通过。

**6. 与已有知识的关系及增量**

检索范围为 `knowledge/drafts/`、`knowledge/graph/draft/`、`archives/`，关键词为 `asterisk`、`TZDIR`、`zoneinfo`、`stdtime`、`localtime`；命中 E315 的 HarmonyOS 时区目录约束。本候选不重复 E315 的通用路径结论，新增 Asterisk stdtime 的加载、默认规则和 watcher 路径同步边界，建议作为补充材料。

| 已核验条目 | 已有内容 | 本次新增 | 建议处理 |
|---|---|---|---|
| `E315` | HarmonyOS 时区目录依赖和运行时路径约束 | Asterisk `localtime.c` 将 `tzload`、默认规则和 watcher 统一接入 `TZDIR` | 补充 |

**7. 来源索引与提交自检**

| 材料 | 路径或链接 | 固定版本及角色 |
|---|---|---|
| 上游源码 | GitHub Asterisk 22.10.1 tarball | SHA-256 `373c98f4...f89663` |
| 修复实现 | `0015-main-stdtime-tzdir-env.patch` | `d0c8db7369` |
| 消费者/反例测试 | `test_package/test.c`；TZDIR path logic | `d0c8db7369` |
| 汇总证据报告 | `archives/a/asterisk/22.10.1/reports/knowledge-evidence.md` | 当前新分支 |
| 原始验证记录 | PR #9563 / CI #44591 | historical，L0 失败 |

- [x] KV 与 MD 同名，`doc_file` 一致，无模板占位符。
- [x] 统计分母明确，未执行不计入通过率。
- [x] 原 PR、修复提交和 CI 失败阶段可追溯。
- [x] 当前新 PR 编号已回填为 #9608，并与远端 HEAD 核对。

最终处理建议：作为 E315 的补充材料提交，保持待维护者审查。剩余动作：提供真实 zoneinfo 目录，单独重跑 TZDIR 相关入口；在此之前不宣称该机制已目标环境通过。
