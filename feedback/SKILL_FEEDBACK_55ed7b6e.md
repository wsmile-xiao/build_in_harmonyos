# SKILL 执行流程反馈报告

> 本报告记录 Rakudo 2025.11 HarmonyOS PC 适配中的构建、测试与流程发现。

---

## 背景

- **软件名称**: rakudo
- **版本**: 2025.11
- **构建日期**: 2026-08-19
- **构建系统**: Perl Configure.pl + Make + Conan 2
- **上游仓库**: https://github.com/rakudo/rakudo
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 0
- **运行依赖**: moarvm/2025.11、nqp/2025.11
- **最终状态**: 本地构建与测试成功；远程提交受依赖发布顺序约束

---

## 情况

### 执行概要

| 阶段 | 步骤 | 结果 | 说明 |
|---|---|---|---|
| init-build | 源码下载与校验 | 完成 | 官方 release tarball，SHA-256 校验通过 |
| build | OHOS arm64 编译 | 成功 | MoarVM 后端，三层运行时使用同一 staging 前缀 |
| conan-verify | 配方验证 | 通过 | G0–G4 全部 PASS |
| finish | W3 本地 CI | 通过 | 上游 166 文件/2757 断言通过，消费者检查通过 |
| W4 | 独立审计 | 整改后复审 | 补充直接依赖、运行环境和包范围断言 |
| submit | PR、AI Review、CI | 待执行 | 需先满足 MoarVM/NQP 发布顺序 |

### 失败与问题

1. Rakudo、NQP 与 MoarVM 必须安装到同一前缀；直接把独立 NQP 可执行文件传给 Rakudo 配置会因前缀不一致失败。配方改为把 MoarVM/NQP 运行闭包复制到 staging 前缀后构建 Rakudo。
2. NQP 的配置要求前缀内存在 MoarVM 的 MAST bootstrap 源；本地依赖验证中补齐该运行时资源后通过。
3. NQP 上游文件操作测试在 HarmonyOS 上因硬链接语义失败；其余测试通过。该问题属于下层 NQP 归档处理范围。
4. Rakudo 在 HarmonyOS 上启用 MoarVM JIT 编译 CORE.c 时出现 SIGBUS；设置 `MVM_JIT_DISABLE=1` 后干净构建、上游测试和运行时验证稳定通过。
5. `finish` 的补丁差异扫描在没有源码编辑追踪器时长时间等待；W3 构建和测试证据已成功生成，凭据由仓库 `FinishPipeline` 写入。
6. 独立 W4 首轮指出缺少直接 MoarVM 依赖、最终运行环境未传播 JIT 开关、包中残留开发文件、消费者统计和 manifest 不一致；均已整改并加入消费者断言。

### 知识图谱使用情况

- **引用知识条目**: 无直接命中
- **新增知识草稿**: 0
- **未覆盖的错误模式**:
  - Rakudo/NQP/MoarVM 运行时要求同前缀布局；
  - NQP 构建依赖 MoarVM 包内 MAST bootstrap 文件；
  - HarmonyOS 上 MoarVM JIT 编译大型 CORE 设置文件可能触发 SIGBUS；
  - 无源码编辑追踪器时 finish 补丁扫描可能卡住。

### AI 检视结果

- **检视阶段到达**: 本地独立 W4
- **变更摘要评估**: 配方使用官方 2025.11 源码，显式声明 MoarVM/NQP，保留必需运行闭包并清理开发文件；测试覆盖真实 Raku 语言行为和包范围。
- **检视意见数量**: 首轮 6 项（3 项 P1、3 项 P2/P3）
- **检视意见处理**: 可修复项全部整改；依赖远端发布状态作为外部顺序约束保留说明。

### CI 结果

- **本地 CI/W3**: PASS
- **上游测试**: 166 files，2757 assertions，Result: PASS
- **消费者测试**: 版本、7 项 Raku 输出及 4 项运行环境/包范围检查
- **conan-verify**: G0–G4 PASS
- **远程 CI**: 待 PR 创建

### 效率分析

- **HANDOFF 次数**: 1
- **重试次数**: 多次，主要用于逐层打通 MoarVM→NQP→Rakudo 和验证 JIT SIGBUS 根因
- **关键瓶颈**: CORE.c.setting.moarvm 单线程编译耗时长，`make test` 会再次生成设置文件
- **耗时较长的步骤**: Rakudo 干净构建、上游 `make test`、conan-verify G2、W4 整改后强制重建

---

## 建议

### SKILL 设计改进

1. W0 对分层语言运行时应支持“本地依赖链验证”模式，并明确区分本地已验证与远端已发布。
2. `finish` 在无源码编辑追踪器且没有补丁时应立即跳过差异扫描。
3. 对耗时项目，W4 包范围整改后应允许复用同一 recipe revision 的上游测试证据，仅重跑 package/test_package。

### 模板改进

1. application 模板应默认传播运行时必需环境变量，并在消费者测试中断言。
2. application 包应默认检查和清理 `include/`、pkg-config 元数据及调试辅助启动器。
3. manifest 模板应支持多个直接运行依赖，而不是单一 `dependency` 字段。

### 自动化补全

1. 自动从 TAP/prove 输出提取 files、assertions 和 PASS/FAIL 并同步到 manifest、报告和反馈。
2. 自动检测包内绝对 Conan 缓存路径和开发元数据。
3. 自动生成最终包文件清单并与 application 白名单/禁止项比较。

### 知识图谱覆盖

1. 新增 Rakudo/NQP/MoarVM 同前缀 staging 的构建模式。
2. 新增 NQP 对 MoarVM MAST bootstrap 资源的构建期依赖。
3. 新增 HarmonyOS 上 MoarVM JIT SIGBUS 与 `MVM_JIT_DISABLE=1` 规避方式。

---

## 作者

- **姓名**: wingsluo
- **邮箱**: wingsluo@noreply.gitcode.com
- **Agent ID**: 4B2B
- **生成时间**: 2026-08-19
- **PR 编号**: 待创建
- **Git Commit**: 待提交
