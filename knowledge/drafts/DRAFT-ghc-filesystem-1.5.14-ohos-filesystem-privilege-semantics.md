# DRAFT-ghc-filesystem-1.5.14-ohos-filesystem-privilege-semantics

> 草稿（Path B 知识库扩展候选）— 仅供主编后续审核分配正式 E 编号，非正式知识条目。
> 依据：ghc-filesystem 1.5.14 r03/r04 实测 evidence（worktree 分支 feat/ghc-filesystem-1.5.14）。

## 问题（Problem）

在 OHOS（HarmonyOS PC / 真机）上运行文件系统类上游测试套件（如 ghc::filesystem 的 Catch2 套件）时，
同一批用例同时触及三类 POSIX 文件系统能力：**hard link（create_hard_link/copy create_hard_links）**、
**FIFO（mkfifo）** 与 **chmod/权限位语义（fs::permissions，owner_write/group_write 位）**。
直接把这些用例的失败等同于"库缺陷"会误判适配质量；反之把平台能力边界当作库缺陷修补（改动上游断言或打补丁绕过）
会污染代码且掩盖真实缺陷。需要一个可复用的诊断框架把"平台能力边界"与"库缺陷"区分开，
并保留逐入口证据与可恢复条件，供后续同平台库复用。

## 根因（Root Cause）

OHOS 真机文件系统与 Linux 桌面假设存在三类系统性差异：

1. **hard link 不可创建**：用户主目录/工作目录挂载于 HMDFS（分布式文件系统，nodev），
   跨设备 inode 不具备唯一性，`link()`/`ln` 返回 `Operation not permitted`（对应既有条目 E079）。
2. **FIFO 不可创建**：SELinux 策略禁止用户进程创建命名管道，`mkfifo()` 返回 `Operation not permitted`
   （对应既有条目 E074 的 FIFO 面）。
3. **chmod() 不生效 / 权限位语义漂移**：SELinux/HMDFS 忽略 POSIX chmod() 调用（返回 0 但权限不变），
   或额外屏蔽 other-read/owner-write 位（对应既有条目 E046/E047）。

这三类能力缺失发生在 **syscall/文件系统层**，与 ghc-filesystem（header-only、纯用户态头文件库）无关，
库本身在这些调用之上没有实现缺陷。上游测试断言这些能力成立，因此在测试环境缺失时失败，
但失败根因全部可归因到平台，而非库。

## 诊断方法 / 最小验证策略（Solution / Minimal Verification）

### 区分平台能力边界 vs 库缺陷的判定流程

1. **逐入口失败分类**：把每个失败断言映射到具体 POSIX 能力：
   hard link / FIFO / chmod 权限位 / 其他。
2. **平台能力探针（最小验证）**：对每个能力运行独立探针，证明是平台拒绝而非库逻辑错误：
   ```sh
   # hard link 探针（工作目录）
   printf x > hl_probe_a && ln hl_probe_a hl_probe_b; echo "hardlink_exit=$?"
   # FIFO 探针
   mkfifo fifo_probe; echo "mkfifo_exit=$?"
   # chmod 探针
   printf x > chmod_probe && chmod ugo-w chmod_probe && stat -c %A chmod_probe
   ```
3. **交叉对照**：失败断言的能力 ∈ 探针证明不可用的能力集合 ⇒ 平台能力边界（非库缺陷）；
   否则进入库缺陷排查（对照知识图谱 error_signature）。
4. **禁止事项**：不得修改上游测试断言；不得用 build-tests=false/宽泛跳过伪造通过；
   不得把受限用例伪写成通过。
5. **证据闭环**：每个入口记录命令、cwd、退出码、首错、绝对日志路径、日志 SHA-256，未运行项单列。

### ghc-filesystem 1.5.14 实测结果（r03）

| 入口 | 结果 | 归因 |
|------|------|------|
| filesystem_test（Catch2 主套件） | 70 cases / 58 pass / 12 fail；937 assertions / 919 pass / 18 fail | 18 项失败全属 hard link/FIFO/chmod 平台能力边界 |
| exception.cpp（-fno-exceptions smoke） | 编译 0 / 运行 0 | 通过 |
| multi1.cpp + multi2.cpp（多翻译单元） | 编译 0 / 运行 0，8 assertions / 2 cases | 通过 |
| fwd_test.cpp + impl_test.cpp（两段式） | 复用全套 70 cases，58/12 | 同平台能力边界 |

## 恢复条件（Recovery Condition）

- 在支持 hard link / FIFO 创建且 chmod 可生效的宿主环境（标准 Linux 桌面、容器或 CI 虚拟机）重跑，
  预期全部用例通过（上游套件在 Linux 上全绿）。
- 在 OHOS 真机上，受限用例如实标记为平台能力边界，不阻塞适配 PR；
  若后续 OHOS 系统版本放宽 SELinux/HMDFS 限制，需重跑台账更新。

## 适用边界（Affected Scope / Applicability）

- 直接适用：任何在 OHOS 真机运行的文件系统 API 上游测试套件（ghc::filesystem、std::filesystem 实现、
  POSIX filesystem 测试、以及依赖文件权限断言的集成测试）。
- 复用价值：判定框架（探针→归因→证据闭环）可推广到其他 C/C++ 库的上游测试失败归因场景。
- 已知限制：本条目只覆盖 hard link/FIFO/chmod 三类能力；其他平台差异（符号链接、
  inode 语义、时间戳元数据等）由 E018/E050/E220 等既有条目覆盖，不在此扩展未验证结论。

## 反例（Counter-examples / 不适用情形）

- 失败断言不涉及 hard link/FIFO/chmod 能力（如纯算法、路径规范化结果错误）⇒ 按库缺陷处理。
- 探针显示能力可用但库用法错误（如传错参数、违反 API 前提）⇒ 失败归因库，不得套用本框架。
- 上游已在代码中显式要求某能力（如 precondition 检查）而 OHOS 无法满足 ⇒ 属于依赖/基础设施阻塞，
  不是"平台能力边界+可恢复"模式，需单独记录。

## 跨库推广范围（Cross-library Scope）

已加工的相邻条目：E046（chmod 不生效）、E047（other-read 位屏蔽）、E074（FIFO Permission denied）、
E079（hard link Operation not permitted）、E220（Perl 工具链存储/权限分叉）。
本条增量：**把三个单能力条目整合为"上游文件系统测试失败归因"的统一诊断框架**，
给出 探针→归因→证据闭环 的判定流程、verbatim 探针命令、逐入口台账模板与恢复条件，
这是 E046/E047/E074/E079 各自单点记录所不覆盖的跨库可复用方法层。

## 证据映射（Evidence Mapping，r03/r04）

- 源码完整性：官方 gulrak/filesystem，tag v1.5.14，release commit `8a2edd6d92ed820521d42c94d179462bf06b5ed3`，
  官方 archive tarball SHA-256 `e783f672e49de7c5a237a0cea905ed51012da55c04fbacab397161976efc8472`
- 上游测试运行日志与 SHA-256：见 notes.md r03 台账（upstream_test.log `0065dbde…`，
  multifile_test.log `cb01fcca…`，fwd_impl_test.log `183d77a0…`，exception_test.log `e3b0c442…`）
- conan create + test_package：exit 0（`PASS: ghc::filesystem header-only API OK`）
- finish/W3：`.ci-result.json` exit_code 0（W3_local_ci）
- 原子性：变更仅限 archives/g/ghc-filesystem/，staged/unstaged/untracked 审计干净
- PR #7338：open（本草稿不更新 PR）

## Issue 草稿字段（Path B 模板，仅草稿，无远端写入）

- 标题前缀：【知识库扩展】
- 主题：OHOS 文件系统测试 hard link / FIFO / chmod 权限语义的平台能力边界归因
- 关联：ghc-filesystem 1.5.14（r03/r04 证据），正式 E 编号待主编分配
- 验收：草稿对 promote 为正式条目并生成 doc/E###.md 与 index 条目