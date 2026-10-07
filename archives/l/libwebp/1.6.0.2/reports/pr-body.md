## PR 信息

- **三方库名称**：libwebp
- **上游版本**：官方 1.6.0；本次适配修复版本 1.6.0.2，不冒称新上游标签
- **上游仓库地址**：https://github.com/webmproject/libwebp
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）；已按当前完整证据逐项重判HD1—HD4，四项均未匹配
- **使用知识库**：E096、E130；本次实质增量配对草稿 E696-draft-LWP2

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 64 | 官方固定 ANTLR 4.12.0 默认启用原用例，原参数化 IDs 分别 32+32；不关闭 BUILD_TESTING |
| 集成测试 | 12 | 官方 libwebp 1.6.0 原 tests/fuzzer 入口，含原基础 7、mux 4、info 1；执行其固定 FuzzTest harness，非只统计注册 |
| 其他测试 | 0 | 该原 CMake 路径未发现独立额外运行入口；精确清单与源审计将附正式证据 |
| **合计** | **76** | 正式 Conan r005 同一事务实际 76/76、零 skip，独立源码 IDs 和 ANTLR 原参数核对通过；不沿用探索 PASS |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 64 | 不变 | 原 ANTLR 测试与断言未修改；仅构建平台能力探测修复 |
| 集成测试 | 16 | +4 | 原 libwebp 12；另有消费者真实无损 RGBA、元数据 mux/demux、有损尺寸/alpha 和坏码流拒绝 4 项 |
| 鸿蒙特有测试 | 1 | 新增 | HarmonyOS PC AArch64 ELF codesign、实际 SONAME/NEEDED 与自有包运行时命名空间、真实 codec 调用的独立专项 |
| **合计** | **81** | **+5** | 正式 Conan r005 与现行官方本地 CI r001 各自同一事务实际 76+4+1 全通过，不拼跨run分母 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

保留全部原 FUZZ_TEST 注册、参数化用例和断言。官方 libwebp patch.sh 在它原定 FuzzTest 源码树执行；ANTLR CMake 只为不在旧平台白名单的真实 Clang 使用实际 C++17 编译/链接能力检查，不降低标准，不伪装系统名。OHOS ELF 链接与签名修复在配方实现，未改测试产品判据。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

消费者 consumer.c 与独立 harmony_signed_loader.py 是新增验收项，不替代原上游 76 项。静态 CHECK 调用点 19 不是运行时用例分母。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：76/76（100%）
- 新增测试用例通过率：5/5（100%）

本文件为待创建新 PR 的六节正文。Issue #3565 已经一次纠正并权威回读，真实修复任务14927（libwebp1.6.0.2，fix/libwebp-1.6.0.2）已导入并领取，账号2301_80739235，活动为开源鸿蒙PC专项积分赛-依赖。正式证据绑定当前实际配方、完整 HEAD/tree、唯一 run、boot/UID、输入 SHA-256、真实 stdout/stderr/RC、原 source case IDs 和完整 WAL/receipt 链。探索 libwebp-native-observed-r004.json 的 76/76 不拼接正式结果；旧 PR #13623 的 Review/CI 不冒充新修复版本的当前 HEAD 门禁。

正式同run证据：libwebp-conan-observed-r005.json SHA-256 `5bb410b2b7eab1e098606f343b9d77fb7d042d244e7d0c4000c7ecbca78792c5`；libwebp-conan-source-cases-observed-r005.json SHA-256 `3c53696cefb28e66b42124da8bd508449cdd89db97bddfbfe63158f8aa22cc48`。当前官方step35 r001使用新增专项目录、清单与固定marker实际执行，原setup/build_and_test RC0、76+4+1和L0/L1通过；原`.ci-result.json`实际由官方方法生成、原日志SHA `b6cf02d05e27386b18038b674b8beb034f23fa14c85a3ca4de8b8d6ed7c0e18f`独立核对。`reports/official-step35-observed.json` SHA `9c44182d456b890bf788d9c0dc151320809ee11c9ce2bf11902f0dfb9c27cd0d`、`reports/upstream-source-cases-observed.json` SHA `10f3be25105582c22a1c8db1c3571a8960e4ea67e8f3487658a3186061a69025`。各run唯一launch/release/postrelease/自有进程0均独立核对，不将任一探索结果冒充正式阶段，也不将本地CI冒充平台CI。

---

## 补充说明

- 关联 Issue：[Issue #3565](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3565)，已权威回读为本账号唯一 OPEN 的真实1.6.0.2修复申请；旧版本历史关联已一次解除并双向回读为空，旧PR保持OPEN且代码HEAD不变。真实任务14927已领取；PRE_CREATE和新PR的POST_CREATE仍须逐阶段实际验证。
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：fix/libwebp-1.6.0.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：此为真实更高修复版本，修复旧配方禁用原测试、缺少鸿蒙专项以及未知平台 C++ 标准/ELF 链接行为；不是同版本重复导入。知识草稿必须配对提交并通过当前门禁。平台正式 Review/CI 未触发，不能称仅等待 CI。
