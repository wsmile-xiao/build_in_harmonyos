# DRAFT-sdl2-mixer-2.8.2-finish-nonblocking-exit

> 配对草稿（与 `DRAFT-sdl2-mixer-2.8.2-finish-nonblocking-exit.kv` 同 stem 同主题）
> 触发事件：sdl2_mixer 2.8.2 适配（R12/R13 本地证据）
> 路径 B 知识库草稿：可复用框架语义发现，不作为框架代码交付。

## 软件与版本上下文

- 库：sdl2_mixer 2.8.2（SDL_mixer，CMake，依赖 sdl2/2.30.10）
- 阶段：finish / 本地验证 / 门禁

## 可复现错误签名

`python3 scripts/ohc-run.py finish sdl2_mixer 2.8.2 built` 在 W3 阻塞门禁、conan-verify、
finalize-archive、test_package 全部通过的情况下仍返回进程退出码 1；日志「失败步骤:
step5b, step8」。

- Step7/10 W5 知识图谱完整性检查：`❌ 知识图谱完整性检查发现 1 类问题`
  （E219/E253/E305 字段缺失 + 213 草稿待审；但 graph validate 通过、知识完整性检查通过）
- Step10/10 submit 就绪预检：`❌ test-report.md / packaging/ / .staging-verified` 3 项未就绪

## 原始证据来源

| 证据 | 原始日志 | SHA-256 |
|---|---|---|
| R12 原始 finish 语义证据 | `/storage/Users/currentUser/tmp/r10-finish.log` | `b37da68f91762a57447e1a64cf4eb622e9be11d2e830cc9577d30afa6b6b1e58` |
| R12 目标 SKILL 语义证据 | `/storage/Users/currentUser/tmp/r12-skill-rules.log` | `ab782b863e5f864ccee2a14b022c943330dcf32cbad28791d6ea73df90dc66a5` |
| R13 完整 finish 证据 | `/storage/Users/currentUser/tmp/r13-finish.log` | `2659129578c65afa8108883200f9e6bc5565855afd224ba9d166f01cf17a105e` |

## 根因

目标 SKILL.md 将 `[7/10] check-knowledge-gap`（W5 知识完整性检查）声明为「非阻塞」、
`[10/10] submit 就绪预检`声明为「警告」，但 finish 驱动 `scripts/ohc/finish.py` 的
`run()` 用 `all(self.steps.values())` 聚合所有步骤状态，step5b 与 step8 为 False 时
使 `return 0 if all_ok else 1` 返回 1。共享框架的退出码聚合语义与 SKILL 声明的门禁
语义冲突：非阻塞/警告步骤不应令进程非零退出，却实际聚合进退出码。

## 最小本地验证方案（临时，仅验证用）

仅在本地验证时临时修改 `scripts/ohc/finish.py` 的 `run()`：

```python
# 退出码仅取决于目标 SKILL 的真实阻塞门禁（W3 本地 CI = step35，内含 W2 结构检查，
# 失败已在上游 sys.exit(1)）；非阻塞 step5b/W5 与警告 step8/submit 就绪保持输出与
# 诊断但不导致非零退出。
blocking = not self.steps.get("step35", False)
return 1 if blocking else 0
```

此改动仅供验证（R13 已证明），验证后必须恢复框架文件至基线；不得作为框架交付。

## 验证

R13 在临时修复 + R05 两项临时修复（finalize_archive release/debug tar 非阻塞、
summary scalar-to-list 提升）同时生效下，完整自然 finish 实际进程退出码为 0，
且 Step5b/W5 与 Step8 警告诊断仍保留输出（未静默）；W3 本地 CI 1/1 通过、
conan-verify G1-G4+L2/L4/L5 全 PASS、`.ci-result.json` exit_code=0；验证后三项框架
文件与 SUMMARY.md 恢复至基线哈希，框架零 diff（证据日志 SHA-256 `26591295...`）。

## 适用边界

- 适用于本地 finish 流程中「SKILL 声明非阻塞/警告但退出码聚合误判」的场景；
- 仅作为可复用框架语义发现，不替代当前库适配；
- 不得推广为对共享框架的持久修改（需框架侧统一退出码聚合语义）；
- 对其他库 R01-R13 同型问题（W5 知识缺口、submit 就绪项）同样适用。

## 安全提示

任何对本库的完成度判定均以真实阻塞门禁（W3/conan-verify/test_package/atomicity）
为准；未达到真实阻塞门禁前不得以「finish 退出码 0」宣称成功。临时框架改动必须在
验证后恢复，不得进入本库 staged/unstaged/untracked/committed/PR 范围。

## 查重差异

- 与 E####-finish 相关条目差异：本条目聚焦「退出码聚合语义 vs SKILL 门禁语义」，
  而非具体编译错误或依赖缺失；
- 与既有 DRAFT（DRAFT-002/2045 等）差异：本条目为框架语义（gate/exit-code）类，
  与下载镜像、SONAME 打包等类别不重叠。
