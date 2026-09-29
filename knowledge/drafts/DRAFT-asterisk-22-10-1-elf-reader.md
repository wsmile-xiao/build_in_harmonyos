**DRAFT-asterisk-22-10-1-elf-reader — HarmonyOS ELF 依赖扫描在缺少 readelf 时回退到 llvm-readobj**

Asterisk 配方在 package 阶段需要解析 ELF 的 NEEDED 条目，才能把传递依赖复制到包内 `lib/`。HarmonyOS 设备镜像不保证存在固定路径的 `llvm-readelf` 或 `readelf`，但可以提供 `llvm-readobj --dynamic-table`；配方应按实际工具能力选择解析器。当前真机验证证明该配方回退不阻断 `conan create` 和 `test_package`，而共享 runner 的固定 `readelf` SONAME 门禁仍是独立的基础设施问题。

**身份与当前结论**

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-asterisk-22-10-1-elf-reader` |
| 配套结构化文件 | `knowledge/drafts/DRAFT-asterisk-22-10-1-elf-reader.kv` |
| 当前状态 | 已有目标环境构建和消费者验证；共享 L5 工具门禁仍待基础设施修复 |
| 建议去向 | 补充既有模式（E019/E078） |
| 实际贡献者 | `gcw_hL6s3dcK`；提交作者 Theresa <ylinzixuan@qq.com> |
| 来源任务/PR | [#9608](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/9608) |
| 提取方式 | 已有 PR 的适配过程提炼 |
| 本次交付 PR | 原位更新 [#9608](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/9608) |
| 包及配方版本 | `asterisk` / `22.10.1` |
| 上游版本与源码 | `22.10.1`；`https://github.com/asterisk/asterisk/archive/refs/tags/22.10.1.tar.gz`；SHA-256 `373c98f4d4a1b923b42def0aee03f4e36aca9d1c244a8eeda646da8a97f89663` |
| 知识来源提交 | `c7893e55704dcb80718b869bdbb46b27dc993505` |
| 被验证提交 | `d66aeaef784ff076f6dfc292dbc81c7e7f2add02` |
| 最后更新 | `2026-09-14` |

本草稿的验证结论是：在 HarmonyOS aarch64 真机上，配方使用可用 ELF reader 完成打包，`conan create` 和 `test_package` 均通过。仍未证明：当前 `5a6a8e0dd7`（其后又加入 profile compiler 和 shell 选择修复）已重新完成真机验证；共享 runner 的 `readelf -d` SONAME gate 也未由本 PR 修复。

**从已有 PR 提取的依据**

原 PR 标题、状态与提取基线：`【知识库扩展】asterisk 22.10.1：full-PBX HarmonyOS 可移植性修复`，当前状态 open；提取基线为文档补写前的 `5a6a8e0dd766f416251869b9cb4e6a4bf1b89ab4`。

| 原 PR 事实 | 具体位置与版本 | 提炼出的可复用机制 | 本次补充 |
|---|---|---|---|
| `_bundle_libs()` 由固定 `llvm-readelf` 改为多工具选择，并对 `llvm-readobj` 使用动态表参数 | `archives/a/asterisk/22.10.1/conanfile.py`；`c7893e5570` | ELF 依赖扫描应按目标实际可执行工具选择，不能绑定固定 HNP 路径 | 形成 KV＋MD 草稿并绑定真机 run |
| runtime/sysroot 候选目录从选定 clang 路径动态推导 | `conanfile.py`；`d66aeaef78` | reader 找到 NEEDED 后，依赖闭包仍需在真实工具链目录查找 | 与 reader 验证结果放在同一证据矩阵，区分 runner L5 |
| 真机 L5 报 `soname_gate_failed` | `codex-22.10.1-asterisk-22.10.1-fix-d66aeaef78-conan-20260914-122529-4453` | 共享门禁固定使用 readelf 时，工具缺失可能产生基础设施误报 | 明确不修改共享 `ci/`，保留为外部阻塞 |

原 PR 已有的贡献：Asterisk 22.10.1 Conan 配方、19 个生产 HarmonyOS 适配补丁、`test_package`、依赖闭包捆绑和 ELF 签名。上游 full-PBX 测试修复补丁已从当前主线剥离。

本次提炼新增的贡献：将“目标设备 ELF 工具能力差异”从具体构建记录提炼为可复用的选择契约，并把配方级 reader 回退与共享 runner 的 SONAME 工具缺失分开记录。

历史记录与本次实验的区分：官方 CI #46520 的 `0016` 应用失败属于较早提交；本次实验是目标 run `...122529-4453` 在 `d66aeaef78` 上完成的 `conan create`/`test_package`，其后 `5c341c2ba6` 和 `5a6a8e0dd7` 的 profile 修复尚未重新上机。

升级依据：该候选新增了既有 E019/E078 未覆盖的“工具能力回退和共享门禁误报边界”，并有真实目标环境构建及消费者结果；因此可以作为补充材料提交，但不能将 L5 误报写成当前包失败已修复。

**1. 触发条件与可辨认现象**

| 条件 | 本次实际值 | 为什么影响结论 |
|---|---|---|
| 目标系统、架构、运行域 | HarmonyOS/OHOS，aarch64，Conan package runner | 设备工具集合与编译机不同，固定 `/data/service/hnp` 路径不可靠 |
| 编译器及构建工具 | Conan 2.x、Autotools、clang 15、`zsh ci/conan/build_and_test.sh` | `_bundle_libs()` 在 package 阶段执行外部 ELF reader |
| 关键依赖及版本 | openldap/2.6.7、libedit/20240808、uuid/2.40.1、jansson/2.15.1、libxml2/2.15.3、sqlite3/3.49.1 | NEEDED 闭包必须从这些依赖目录和工具链 runtime 目录解析、复制 |
| 文件系统、路径、权限或硬件 | 真机没有 runner 所调用的 `readelf`，提供 `llvm-readobj`；工具链路径由 profile 和选定 clang 决定 | reader 选择和 L5 gate 的结果会受工具存在性影响 |
| 最小输入与前置步骤 | 使用 OHOS profile 执行 Asterisk 22.10.1 单包 `conan create` 和 `test_package` | 同时验证包构建、依赖闭包和消费者入口 |

首次可定位的失败：EVID-03 的目标 runner L5。

```text
L5_RESULT=fail: soname_gate_failed
```

建议错误签名：`soname_gate_failed`。

签名验证：失败样本为上述真机 L5 输出，命中 `soname_gate_failed`；正常/无关样本为同一 run 的 `runner rc=0`、`conan create=通过` 和 `test_package=通过`，不命中该签名。该对照说明 gate 失败不能直接等同于包构建失败。

**2. 根因与排除项**

`_bundle_libs()` 需要读取每个 ELF 的 NEEDED 条目，再从依赖目录复制传递闭包。早期实现把 reader 固定为 `llvm-readelf` 或固定 HNP 路径；当目标镜像只提供 `llvm-readobj` 时，配方无法完成扫描。当前实现按 `llvm-readelf`、`readelf`、`llvm-readobj` 选择，并将最后一种映射到 `--dynamic-table`，因此 package 阶段可以继续完成。真机 L5 的 `soname_gate_failed` 则来自共享 runner 固定执行 `readelf -d`，它不是 `conan create` 或 `test_package` 的失败；本 PR 受范围约束没有修改共享 `ci/`。

| 可能原因 | 检查方法与证据 | 结论 |
|---|---|---|
| 配方无法解析 NEEDED，导致依赖闭包不完整 | 目标 run 的 `conan create`、package 阶段和 `test_package` 结果 | 已排除为当前 package 阻塞；reader 回退工作 |
| 包中确实没有 SONAME | L5 的 `soname_gate_failed` 输出 | 不能据此成立；runner 未使用设备可用的 `llvm-readobj`，需由门禁工具修复后再判断 |
| 依赖库目录固定在旧 HNP 路径 | 对照 `d66aeaef78` 的 clang 路径动态候选修复及旧路径告警消失 | 已排除旧固定路径问题；当前提交仍需真机重验 |

共同变化条件：目标 run 同时包含 reader 回退 `c7893e5570` 和 runtime/sysroot 候选修复 `d66aeaef78`；因此 run 证明组合后的 package/test 契约，但不把 L5 gate 归因给任一 Asterisk 源码补丁。

**3. 最小修复与选择条件**

1. 在 `_bundle_libs()` 中按可执行文件存在性选择 `llvm-readelf`、`readelf` 或 `llvm-readobj`。
2. 对 `llvm-readobj` 使用 `--dynamic-table`，继续提取 `Shared library: [...]` 中的 NEEDED 名称；对其他 reader 保持 `-d`。
3. 复用此方案前必须确认目标 LLVM 工具确实支持所选参数，并独立核对 clang 对应的 runtime/sysroot 目录；共享 runner 的 SONAME 检查必须另行支持同等工具回退。

实际修复来源：[`conanfile.py`](../../archives/a/asterisk/22.10.1/conanfile.py)；[`c7893e5570`](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/commit/c7893e55704dcb80718b869bdbb46b27dc993505)。

```sh
python -m py_compile archives/a/asterisk/22.10.1/conanfile.py
zsh ci/conan/build_and_test.sh archives/a/asterisk/22.10.1
```

上面的第一条命令适用于宿主语法检查；第二条命令适用于已准备 OHOS aarch64 profile、依赖制品和真机 runner 的目标环境。回退方案为直接使用 `llvm-readelf -d`，但仅在目标设备确实提供该工具时成立；当前 run 证明了 `llvm-readobj` 路径，未证明所有 LLVM 版本的输出格式完全一致。

**4. 验证矩阵与证据绑定**

| 证据 ID | 类型 | 提交、环境与输入 | 命令/测试入口 | 实际结果 | 日志/附件、定位与哈希 |
|---|---|---|---|---|---|
| EVID-01 | historical | `5a6a8e0dd7` 之前的官方 CI #46520；OHOS aarch64 profile | `zsh ci/conan/build_and_test.sh` | L0/KC/JC 通过；应用 `0016` 时失败，未进入 test_package | PR #9608 评论中的 CI #46520 日志；错误为 patch hunk 不匹配 |
| EVID-02 | host-executed | `c7893e5570` 的配方 reader 改动 | `python -m py_compile archives/a/asterisk/22.10.1/conanfile.py` | 通过 | 当前 worktree 语法检查；源码提交见上 |
| EVID-03 | target-executed | `d66aeaef784ff076f6dfc292dbc81c7e7f2add02`；HarmonyOS aarch64 真机 | `zsh ci/conan/build_and_test.sh archives/a/asterisk/22.10.1` | runner rc=0；`conan create` 通过；`test_package` 通过；L5 报 `soname_gate_failed` | `/storage/Users/currentUser/ohos-test-runs/codex-22.10.1-asterisk-22.10.1-fix-d66aeaef78-conan-20260914-122529-4453` |
| EVID-04 | static | 当前 `5a6a8e0dd7` 配方代码 | `_bundle_libs()` reader 分支与候选目录审查 | 代码已包含 reader 回退、clang 动态目录和 profile tool/shell 选择；当前 HEAD 未重新上机 | `archives/a/asterisk/22.10.1/conanfile.py`；最终 PR HEAD 另行记录 |

**被验证文件范围**

| 文件或输入 | 验证时版本/哈希 | 与当前提交的关系 |
|---|---|---|
| `archives/a/asterisk/22.10.1/conanfile.py` | target run 使用 `d66aeaef78`；当前 blob 以后包含 `5c341c2ba6`、`5a6a8e0dd7` | 改变并需当前 HEAD 真机重验 |
| `archives/a/asterisk/22.10.1/patches/`、`test_package/`、`conandata.yml` | target run 使用 `d66aeaef78` | 与当前行为相关输入未改变 |
| OHOS profile、依赖制品和工具 | `os=OHOS`、`arch=armv8`、clang 15；依赖版本见上 | target run 的外部输入；runner L5 工具集合仍不完整 |

被验证提交之后的变化：`5c341c2ba6` 增加 profile compiler 回退，`5a6a8e0dd7` 增加可用 shell 选择；本次只补写文档并新增草稿不会改变已有 reader 逻辑，但两项配方变化仍使当前 HEAD 缺少完整真机复验。

**测试统计**

| 测试层与明确范围 | 计数单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 库存依据及未执行原因 |
|---|---|---:|---:|---:|---:|---:|---|
| 上游 Asterisk full-PBX | 用例 | 724 | 0 | 0 | 0 | 724 | 赛事方人工检视确认库存为 724；当前生产适配 PR 不执行该套件，不能计算通过率 |
| 已安装包消费者 `test_package` / `asterisk -V` | 断言 | 1 | 1 | 0 | 0 | 0 | 真机 run；输出为 `Asterisk 22.10.1` |
| 配方 ELF NEEDED 扫描 | 操作 | 1 | 1 | 0 | 0 | 0 | 同一 `conan create` 成功完成 package 阶段；不等同于共享 L5 gate |
| 共享 runner SONAME gate | 检查 | 1 | 0 | 1 | 0 | 0 | 目标 run 报 `soname_gate_failed`；runner 固定调用缺失的 `readelf`，属于外部工具缺口 |

各行分别统计，不相加制造总数。上游测试通过率为 `N/A（未执行；不纳入本 PR 验收）`。证据等级为 target-executed、host-executed、static 和 historical 的组合；不能从 package/test_package 结果推导 full-PBX 结果，也不能从 runner gate 误报推导包 SONAME 缺失。

**5. 适用边界与禁止做法**

| 可复用前提 | 已验证范围 | 未验证或不适用范围 |
|---|---|---|
| 目标镜像至少提供一个能输出动态表的 LLVM/GNU ELF reader，且 `llvm-readobj` 输出包含 `Shared library:` | Asterisk 22.10.1 package 阶段的 NEEDED 扫描和依赖复制在 `d66aeaef78` 真机 run 中完成 | 当前 `5a6a8e0dd7` 的完整真机复验、所有 LLVM 版本输出格式、共享 runner 的 L5 修复和 full-PBX |

| 错误做法 | 为什么不成立 | 可观察后果 |
|---|---|---|
| 固定 `/data/service/hnp/bin/llvm-readelf` 或直接跳过 NEEDED 扫描 | 工具路径和工具名属于设备能力，不是稳定的包输入；跳过会丢失传递闭包 | 构建失败或包在设备上运行时缺少依赖 |
| 把 `soname_gate_failed` 直接当作 Conan/package 失败 | 当前 gate 使用的 `readelf` 不存在，未完成有效 SONAME 检查 | 错误阻断已通过 `conan create`/`test_package` 的包，并掩盖基础设施缺口 |

能力缺失必须由工具存在性、命令退出码和输出内容区分；当前 L5 是失败，不是 skip，因为 runner 已执行检查但检查器选择了不可用工具。修复共享 runner 需要另起基础设施 issue/分支/PR，不纳入 Asterisk 制品适配 PR。

**6. 与已有知识的关系及增量**

| 已核验的条目/草稿/前序 PR | 已有内容 | 本次新增机制、边界或证据 | 建议处理 |
|---|---|---|---|
| `E019`、`E078` | 使用 LLVM ELF 工具检查 NEEDED/BIND 等动态信息 | 在 OHOS 工具集合不完整时的 reader 能力选择、参数映射和 runner 误报边界 | 补充 |
| `DRAFT-asterisk-22-10-1-tzdir` | Asterisk 22.10.1 运行时 TZDIR 路径适配 | 本草稿只补充 package ELF reader，不重复 TZDIR 机制 | 并列案例，不合并 |

检索范围与关键词：`knowledge/graph/`、`knowledge/drafts/`、`archives/`；检索 `llvm-readobj`、`llvm-readelf`、`readelf`、`ELF NEEDED`、`soname_gate_failed`。命中 E019/E078 的通用 ELF 检查模式，以及 E322 的 SONAME 缺失案例；未命中“OHOS 仅有 llvm-readobj 时配方 reader 回退”的同一机制。

是否属于同一任务重提或版本修订：属于 PR #9608 当前适配过程的知识提炼，不是 full-PBX 测试修复 PR #9561/#9562/#9563 的重提。复用了 E019/E078 的 ELF 动态信息检查概念；本次不重复计作增量的是普通 NEEDED/SONAME 检查本身。

**7. 来源索引与提交自检**

| 材料 | 路径或链接 | 固定版本及角色 |
|---|---|---|
| 上游源码 | Asterisk 22.10.1 GitHub tarball | SHA-256 `373c98f4d4a1b923b42def0aee03f4e36aca9d1c244a8eeda646da8a97f89663` |
| 修复实现 | `archives/a/asterisk/22.10.1/conanfile.py`；commit `c7893e5570` | recipe reader source commit |
| 消费者/反例测试 | `archives/a/asterisk/22.10.1/test_package/`；真机 runner L5 | validated commit `d66aeaef78`；L5 为外部反例 |
| 汇总证据报告 | `archives/a/asterisk/22.10.1/reports/knowledge-evidence.md` | 当前 PR 材料 |
| 原始验证记录 | 真机 run `...122529-4453` | target-executed；完整日志需访问该设备路径 |

提交前填写真实检查结果：

- [x] ID、两个文件名和 KV 的 `doc_file` 一致，中央目录预审能够发现这份 KV。
- [x] KV 字段均为单行，关键字段与本文一致，无模板占位符。
- [x] 引用路径存在；新增草稿和报告进入当前 PR 范围。
- [x] 包版本、上游版本、PR 标题、验证提交及正文测试统计已区分当前 HEAD 与 target run。
- [x] 关键结论有证据；未知、未执行和历史状态已明确标记。
- [x] 已搜索重复材料并说明相对 E019/E078 的增量。
- [x] 当前已有 PR #9608，原有适配贡献与本次知识提炼已区分。

最终处理建议：作为 E019/E078 的补充材料提交，保持待维护者审查；共享 runner 的 `readelf` 回退另行处理。
原 PR 升级建议：支持原位更新 #9608；新增草稿、证据报告和正文必须同步，不能宣称 full-PBX 通过或 L5 已修复。
剩余问题及下一项具体动作：将当前 5a6a8e0dd7 推送后触发官方 CI；若仍出现 `soname_gate_failed`，由独立基础设施 PR 修复 runner 的 ELF reader 选择。
