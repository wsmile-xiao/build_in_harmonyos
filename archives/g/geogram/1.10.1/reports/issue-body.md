# Geogram 1.10.1 HarmonyOS PC 适配申请

申请人账号：2301_80739235
队伍名称：天天开心
申请日期：2026-09-06
库名称：geogram
版本：1.10.1

## 申请事项

申请将官方 Geogram 1.10.1 release asset 适配为 OpenHarmony PC aarch64 Conan 包，分支为 `feat/geogram-1.10.1`。

## 适配与验证

- 官方 release asset SHA-256：`30033340a0dfd86f9e15a8ffdd7c1e6d49b967d3f26fb96cf3dfd1a502d8eba2`
- W0：release asset 已内置第三方源码，无 Conan 外部依赖。
- W3：目标设备 `10.62.150.125:8022` exact-byte transfer/readback、AArch64 构建、原生 self-sign、消费者运行 `RUN_RC=0`，随后释放并通过 post-release readback。
- W4：11 个可参数化上游 `src/tests` 在 MinGW host `11/11`；`test_package` 真实调用 `GEO::initialize` 和 `GEO::vec3`，本地与目标消费者均返回 0。

## 知识库查重情况

已检索 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations`。E549 是本次新增知识草稿，提炼了“上游没有 OHOS 平台枚举时，以任务内 `OHOS-clang` 配置复用 Linux clang 能力且去除 x86-only flags，并用目标原生 signer 闭包完成共享库加载验证”的跨库方法。

## 当前状态与边界

代码和验证证据已冻结在当前候选；Issue 创建后将通过两阶段 Pre-PR 合同绑定真实 Issue/PR 编号、当前 HEAD/tree 和双向关联。平台 CI 必须对当前 HEAD 明确 PASS 后才点击提审。
