**DRAFT-libksba-1-6-7-1-device-local-autotools-staging — libksba 1.6.7.1 OHOS Autotools 设备本地 staging 与测试生命周期**

libksba 的 Autotools 配方在 OHOS Worker 上不能把 Conan/HMDFS 工作目录当作可执行目录。PR #8621 将源码、构建目录和临时目录迁移到设备本地 staging，显式设置 OHOS musl 的 build/host，并保留 `make check` 与 `DESTDIR` 安装；CI #41174 对 7 个上游测试和 1 个消费者测试均报告通过。

**身份与当前结论**

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-libksba-1-6-7-1-device-local-autotools-staging` |
| 配套结构化文件 | `knowledge/drafts/DRAFT-libksba-1-6-7-1-device-local-autotools-staging.kv` |
| 当前状态 | 已有验证证据待审 |
| 建议去向 | 新增模式 |
| 实际贡献者 | `zxyAtom` |
| 来源任务/PR | [PR #8621](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/8621) |
| 提取方式 | 已有普通 PR 升级 |
| 本次交付 PR | 原位升级 #8621 |
| 包及配方版本 | `libksba` / `1.6.7.1` |
| 上游版本与源码 | libksba 1.6.7；https://gnupg.org/ftp/gcrypt/libksba/libksba-1.6.7.tar.bz2；SHA256 `cf72510b8ebb4eb6693eef765749d83677a03c79291a311040a5bfd79baab763` |
| 知识来源提交 | `4bbae1b2a8e6120b9992aab55f51c2ce67de87c9` |
| 被验证提交 | `4bbae1b2a8e6120b9992aab55f51c2ce67de87c9` |
| 最后更新 | 2026-09-07 |

验证结论：CI #41174 的 Buildbot 46796 在同一 PR HEAD 上完成配置、构建、测试和清理，正文记录上游测试 7/7、消费者 1/1。仍未证明 `ksba-config` 在任意安装前缀下可重定位；其补丁含固定 `/storage/Users/currentUser/usr/local` 路径，需后续独立验证。

**从普通 PR 提取的依据**

原 PR 标题、状态与提取基线：`【依赖项】fix(libksba): 1.6.7.1 补齐 OHOS Conan 配方`，open，HEAD `4bbae1b2a8e6120b9992aab55f51c2ce67de87c9`。

| 原 PR 事实 | 具体位置与版本 | 提炼出的可复用机制 | 本次补充 |
|---|---|---|---|
| 显式 `--build/--host=aarch64-unknown-linux-musl` 并建立本地源码/构建根目录 | `archives/l/libksba/1.6.7.1/conanfile.py`，提交 `4bbae1b2` | OHOS Autotools 包应把执行型 configure、编译和临时文件放在设备本地可执行 staging | 草稿与失败/成功证据绑定 |
| 顺序执行 `make`、`make check`、安装到 `DESTDIR`，再复制回 Conan 包 | 同上；`test_package/test.c` | 测试生命周期和安装产物必须在同一 staging 上闭环，不能只看打包成功 | CI #41174 重验 |
| 早期 CI #41169/#41171 出现 `cannot run C compiled programs`，后续 #41174 成功 | PR 评论及 CI 任务 | `--host` 不是单独修复；路径、TMPDIR、依赖脚本和执行域共同决定结果 | 报告列出历史失败与成功边界 |

原 PR 已有的贡献：新增 libksba 1.6.7.1 Conan 配方、OHOS musl 配置补丁、上游测试 manifest、设备本地执行 staging 和消费者 smoke test。本次提炼新增的是可迁移的 Autotools/Conan staging 生命周期及其失败诊断契约。

历史记录与本次实验的区分：失败日志来自 #41169/#41171 评论，成功结果来自 #41174/build 46796；本次只增加草稿、证据报告并做静态一致性检查，未改变实现输入。

升级依据：该 PR 同时提供了可定位的 configure 失败、路径级修复和成功 CI，且 E064/E060 只覆盖通用 conftest 或 HMDFS 权限；本候选新增了 Conan 配方中依赖脚本、TMPDIR、DESTDIR 和测试顺序的组合契约。

**1. 触发条件与可辨认现象**

| 条件 | 本次实际值 | 为什么影响结论 |
|---|---|---|
| 目标系统、架构、运行域 | HarmonyOS PC/aarch64，OHOS CI Worker | configure 生成的测试 ELF 需要在目标运行域执行 |
| 编译器及构建工具 | Conan 2、Autotools、make、clang OHOS musl | build/host 和依赖配置脚本由工具链决定 |
| 关键依赖及版本 | libgpg-error（`gpgrt-config`、`gpg-error-config`） | configure 及链接阶段必须找到同一 staging 的依赖 |
| 文件系统、路径、权限或硬件 | Conan/HMDFS 缓存受限；源码、build、TMPDIR、DESTDIR 使用 `/data/storage/el2/base/cache/libksba-*` 下本地目录 | 执行权限和临时文件可写性决定 conftest 与测试能否运行 |
| 最小输入与前置步骤 | 复制源码到本地根目录，导出依赖 PATH/LD_LIBRARY_PATH 后运行 configure | 保持 configure、测试和安装处于同一执行域 |

首次可定位的失败：EVID-01，CI #41169/#41171 评论中的 `config.log`。

```text
configure: error: cannot run C compiled programs.
If you meant to cross compile, use '--host'.
```

建议错误签名：`cannot run C compiled programs|conftest.*inaccessible or not found|configure.*cross compile`。

签名验证：失败样本 #41169/#41171 命中；成功样本 #41174 的最终状态为 success，未报告上述片段。

**2. 根因与排除项**

Autotools configure 需要编译并执行 conftest。#41169 的默认目录执行失败；#41171 在补充 `--host` 后仍失败，说明参数本身不能修复执行域。#8621 随后把源码、构建和 `TMPDIR` 放入设备本地目录，配置依赖脚本与动态库路径，使用显式 OHOS musl build/host，并在同一目录完成 `make check` 和 `DESTDIR` 安装；#41174 成功支持该因果链。这里对目录限制的归因由失败日志和修复 diff 共同支持，对具体安全策略属于推断。

| 可能原因 | 检查方法与证据 | 结论 |
|---|---|---|
| 仅缺少 `--host` | #41169 与 #41171 的前后失败评论 | 已排除为充分修复 |
| Conan/HMDFS 执行或 TMPDIR 权限 | 失败日志、`conanfile.py` 的本地根目录与 `TMPDIR` 设置 | 主要根因，目标执行证据支持 |
| libgpg-error 配置脚本或链接路径错误 | 配方显式设置 `gpgrt-config`/`gpg-error-config` 和 PATH/LD_LIBRARY_PATH；#41174 成功 | 成功构建中已排除 |

**3. 最小修复与选择条件**

1. 为每次配方计算独立的设备本地 root，并复制源码、build 和临时目录到该 root。
2. 显式传入 `--build=aarch64-unknown-linux-musl`、`--host=aarch64-unknown-linux-musl`，配置依赖脚本及运行库搜索路径。
3. 在同一 root 依次执行 `make -j1`、`make check -j1` 和 `make install DESTDIR=stage`，最后将 stage 复制入包。

实际修复来源：[PR #8621 commit `4bbae1b2`](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/commit/4bbae1b2a8e6120b9992aab55f51c2ce67de87c9)，文件 `archives/l/libksba/1.6.7.1/conanfile.py`。

```sh
./configure --build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl
make -j1
make check -j1
make install DESTDIR=<device-local-stage>
```

命令适用于已准备好本地源码/build/TMPDIR、libgpg-error 配置脚本和运行库路径的 OHOS Worker。未验证回退方案。

**4. 验证矩阵与证据绑定**

| 证据 ID | 类型 | 提交、环境与输入 | 命令/测试入口 | 实际结果 | 日志/附件、定位与哈希 |
|---|---|---|---|---|---|
| EVID-01 | historical | #41169/#41171，PR 修复前后构建尝试 | Conan configure | `cannot run C compiled programs`；#41171 加 `--host` 后仍失败 | PR 评论；任务绑定 #8621 |
| EVID-02 | target-executed | PR HEAD `4bbae1b2`，Buildbot 46796，OHOS Worker | configure → make → make check → install | CI #41174 success，7 个步骤全 success，耗时 411s | [build 46796](https://ohpcd.atomgit.com/ci/build/46796)，task #41174 |
| EVID-03 | target-executed | 同一 HEAD，Conan test_package | `test.c` 调用 `ksba_check_version(0)` | 消费者 1/1 通过 | PR 正文测试统计，构建任务 #41174 |

**被验证文件范围**

| 文件或输入 | 验证时版本/哈希 | 与当前提交的关系 |
|---|---|---|
| `archives/l/libksba/1.6.7.1/conanfile.py`、6 个补丁 | PR HEAD `4bbae1b2` | 相同 |
| `test_package/CMakeLists.txt`、`MANIFEST.yml`、`test.c` | PR HEAD `4bbae1b2` | 相同 |
| OHOS CI Worker、Conan 2、libgpg-error | Buildbot 46796 | 成功运行环境；版本明细以 CI 配置为准 |

被验证提交之后的变化：只增加本草稿和证据报告，未改变上述实现、测试或依赖输入；最终远端 HEAD 在升级回执中记录。

**测试统计**

| 测试层与明确范围 | 计数单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 库存依据及未执行原因 |
|---|---|---:|---:|---:|---:|---:|---|
| libksba 上游测试 | 测试程序 | 7 | 7 | 0 | 0 | 0 | PR 正文与 #41174 成功摘要 |
| 已安装包消费者 | 测试程序 | 1 | 1 | 0 | 0 | 0 | `test.c` 的 `ksba_check_version(0)` |
| 修复边界与反例 | 构建尝试 | 3 | 1 | 2 | 0 | 0 | #41169/#41171 失败与 #41174 成功；不是同一测试套件 |

证据等级限制：EVID-02/03 为目标 CI 实跑；EVID-01 为历史日志；`ksba-config` 固定路径可重定位性和独立真机复验未覆盖。

**5. 适用边界与禁止做法**

| 可复用前提 | 已验证范围 | 未验证或不适用范围 |
|---|---|---|
| Autotools 会执行目标 conftest，且 OHOS 提供设备本地可执行目录 | libksba 1.6.7.1、aarch64、Conan 2、OHOS Worker | 其他架构、没有本地执行权限的 Worker、共享库/非 musl 组合 |
| 依赖配置脚本和运行库可放入同一 staging | libgpg-error、`make check`、DESTDIR 安装 | 无依赖脚本或不同前缀的 `ksba-config` 尚未验证 |

| 错误做法 | 为什么不成立 | 可观察后果 |
|---|---|---|
| 只在 Conan/HMDFS 缓存运行，或只加 `--host` | 没有解决执行/临时目录权限，且可能跳过真实检测 | conftest 失败、错误 cross compile、后续测试或安装失败 |

**6. 与已有知识的关系及增量**

| 已核验的条目/草稿/前序PR | 已有内容 | 本次新增机制、边界或证据 | 建议处理 |
|---|---|---|---|
| E064 | 通用 Autotools conftest 执行失败及误判 cross compile | Conan 配方级本地源码/build/TMPDIR/DESTDIR 生命周期与依赖脚本组合 | 新增 |
| E060 | HMDFS 权限与本地 tmpfs 边界 | 将该边界落实到 Conan 包的可执行 staging，并用 make check/install 闭环 | 补充 |

检索范围与关键词：`knowledge/graph`、`knowledge/doc`、`knowledge/drafts`、`archives/l/libksba`；关键词 `cannot run C compiled programs`、`conftest`、`TMPDIR`、`AutotoolsToolchain`、`DESTDIR`、`make check`。命中 E064/E060，无同一 libksba staging 草稿。

不是同一任务重提或版本修订：同版本重复 PR 只作为去重检查，本次原位升级 #8621，不新建重复知识 PR。复用 E064 的通用诊断和 E060 的路径权限知识，不重复计作增量。

**7. 来源索引与提交自检**

| 材料 | 路径或链接 | 固定版本及角色 |
|---|---|---|
| 上游源码与配方元数据 | PR #8621 `conandata.yml` | libksba 1.6.7.1；SHA256 `cf72510b8ebb4eb6693eef765749d83677a03c79291a311040a5bfd79baab763` |
| 修复实现 | [commit `4bbae1b2`](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/commit/4bbae1b2) | 本地 staging、configure、测试和安装 |
| 消费者/反例测试 | PR #8621 `test_package/`；#41169/#41171 | `test.c`；历史失败 |
| 汇总证据报告 | `archives/l/libksba/1.6.7.1/reports/knowledge-evidence.md` | 与本次提交同版本 |
| 原始验证记录 | [CI build 46796](https://ohpcd.atomgit.com/ci/build/46796) | task #41174，success |

- [x] ID、两个文件名和 KV 的 `doc_file` 一致。
- [x] KV 字段均为单行，根因、签名、方案与本文一致。
- [x] 来源 PR、提交、包路径和测试入口可回溯；证据报告随升级提交。
- [x] 测试统计区分历史失败、当前上游测试和消费者测试。
- [x] 已搜索 E064、E060 和本地草稿，明确新增范围。
- [ ] 远端文件与最终 HEAD：文档提交后回读完成。

最终处理建议：作为 libksba/Autotools 设备本地 staging 的新知识候选提交。
原 PR 升级建议：支持原位升级；#8621 保持同一贡献分支，CI #41174 已通过，人工审批和合并检查仍由平台流程处理。
剩余问题及下一项具体动作：回读远端新增文件、PR 标题/正文和最终 HEAD；后续单独验证 `ksba-config` 重定位。
