## PR 信息

- **三方库名称**：libxt
- **上游版本**：1.3.1
- **上游仓库地址**：https://xorg.freedesktop.org/archive/individual/lib/libXt-1.3.1.tar.xz
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：复用 E228、E236 与 E331 草稿；新增 `knowledge/drafts/E336-draft-2301.kv` 和同 stem `.md`

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 20 | `make -j1 check`：Alloc 18、Converters 1、Event 1；16 PASS + 4 exact expected SKIP |
| 集成测试 | 0 | 上游未注册独立集成入口 |
| 其他测试 | 0 | 上游未注册其他测试入口 |
| **合计** | **20** | **16 PASS、4 exact expected SKIP、0 FAIL、20 nonfailed** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 20 | 不变 | 保留完整上游注册清单和四个目标 ABI 条件 SKIP |
| 集成测试 | 0 | 不变 | 上游没有独立集成入口 |
| 鸿蒙特有测试 | 2 | +2 | 安装包 allocation/context consumer，shared/static 都执行但各只计一次 |
| **合计** | **22** | **+2** | **18 PASS、4 expected SKIP、0 FAIL；断言元数据 20 不计入分母** |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

配方仅在任务私有源码副本中把 `test/Alloc.c` 三处随机正常分配的乘积限制为 1 MiB，避免进程级 `RLIMIT_AS` 下随机正常用例耗尽剩余地址空间。20 个注册路径、断言、oversize/overflow 请求、FAIL 和四个条件 SKIP 语义均保持不变；精确替换计数在上游漂移时失败关闭。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游已有 20 项完整注册清单。新增两个 consumer 用于安装包公共 API 与上下文生命周期验证，不替代任何上游注册项。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：16/20（80%，另有 4 个精确 expected SKIP；完整注册分母保持 20）
- 新增测试用例通过率：2/2（100%）

最终 staged candidate 在真机 `10.62.215.229:2222` 完成一次 W3 launch（runner/outer SSH RC0，shared/static `conan create` RC0），上游 16 PASS + 4 exact expected SKIP / 20，消费者 2/2 PASS，独立总计 18 PASS + 4 SKIP / 22，独立 result validator 通过。精确 run、归档 SHA-256、HEAD tree、staged tree、runner、wrapper 与 W4 身份由提交前外部不可变证据绑定，不在本 staged 报告中自引用；PR 页面在 push 后回读这些最终值。Buildbot #28987 仅是旧 PR HEAD 的历史失败，producer-prefix 修复保持静态收窄；exact-HEAD CI 必须在 push 后重新核验。官方 `finish ... built` 因旧本地环境缺失原始 tarball、G2/setup.sh 失败，未生成新的 `.ci-result.json`，没有手工创建或修改该文件。

---

## 补充说明

- 关联 Issue：#1958
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/libxt-1.3.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：本任务是 OpenJ9 0.59.0 Issue #1084 的真实前置依赖，对应 lowercase contrib 任务 3715。live main 四范围查重没有发现与目标 ABI 条件 SKIP 透明计数等价的条目，故 E336 草稿对随本软件 PR 提交；mixed-case `libXt/1.3.1` 历史行未领取且未使用。中央 Pre-PR 工具仍要求 `passed == inventory` 且 `skipped == 0`，因此不会把四个 SKIP 伪报为 PASS 或把上游分母缩为 16。
- Pre-PR 合同例外（申请人已授权）：本次允许忽略中央合同对 `skipped == 0`、`passed == inventory` 和验证栏 `N/N（100%）` 的机械阻塞，原因是 AArch64 上游 API 的 32 位 `unsigned` 参数无法表达四个 overflow 输入，官方测试按原语义输出精确 expected SKIP。真实清单、SKIP ID/原因、原始日志哈希和 W4 证据均保留，未修改统计分母或伪造 PASS。
