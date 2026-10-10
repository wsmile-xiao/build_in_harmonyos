## PR 信息

- **三方库名称**：libwebp
- **上游版本**：官方 1.6.0；本次适配修复版本 1.6.0.2，不冒称新上游标签
- **上游仓库地址**：https://github.com/webmproject/libwebp
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C（GUI 图像链高难度挑战候选申请）；HD1—HD4 四项仍未证明匹配，候选申请不等于官方认定或分值批准，详见唯一关联 Issue #3565。
- **使用知识库**：E096、E130；本次实质增量配对草稿 E2026100907-draft-LWP2。旧 E696 已被主线其他贡献占用，本次只迁移本 PR 草稿对，保留他人条目不变。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 64 | 官方固定 ANTLR 4.12.0 默认启用原用例，原参数化 IDs 分别 32+32；不关闭 BUILD_TESTING |
| 集成测试 | 12 | 官方 libwebp 1.6.0 原 tests/fuzzer 入口，含原基础 7、mux 4、info 1；执行其固定 FuzzTest harness，非只统计注册 |
| 其他测试 | 0 | 该原 CMake 路径未发现独立额外运行入口；精确清单与源审计将附正式证据 |
| **合计** | **76** | 当前严格签名入口修复候选在官方 step35 r004 同一事务实际 76/76、零 skip；逐项核对原 FuzzTest IDs 和 ANTLR 原参数，不拼跨run分母 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 64 | 不变 | 原 ANTLR 测试与断言未修改；仅构建平台能力探测修复 |
| 集成测试 | 16 | +4 | 原 libwebp 12；另有消费者真实无损 RGBA、元数据 mux/demux、有损尺寸/alpha 和坏码流拒绝 4 项 |
| 鸿蒙特有测试 | 1 | 新增 | HarmonyOS PC AArch64 ELF codesign、实际 SONAME/NEEDED 与自有包运行时命名空间、真实 codec 调用的独立专项 |
| **合计** | **81** | **+5** | 当前修复候选在官方本地 CI r004 同一事务实际 76+4+1 全通过，不拼跨run分母 |

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

2026-10-11 后续整改：真实 AtomCode 检视发现签名入口的格式边界和测试树元数据问题。严格签名模式现在拒绝短头、错误 magic、ELF32、大端以及非执行/共享对象；编译器包装器区分 -c/-S/-E/-fsyntax-only 纯编译动作，不要求签名合法的 ET_REL 对象，真正链接仍保留签名及非零退出失败传播。直接把所有 ET_REL 都判为失败会破坏上游编译探测，因此没有采用这一错误修法。MANIFEST 动态路径与真实 Conan 参数绑定。本机定向12/12后，fresh 官方 FinishPipeline.step35_local_ci r004 实际干净 Conan 构建及76+4+1同run全通过。完整28文件的真实检视报告SHA256为0a5bdc13e322d032c9fb0601e8be5dd881c5cc4169af59790d0fa9a9e34e41bf，公开报告及处置说明为评论193169907；两个大型原始日志仅哈希绑定摘录，该检视不冒充完整逐行日志审核。新提交后另行回读该完整HEAD评审与平台CI。

本文件为 PR #14954 的六节正文。Issue #3565 与本 PR 双向唯一关联，真实修复任务14927（libwebp1.6.0.2，fix/libwebp-1.6.0.2）已领取，账号2301_80739235，活动为开源鸿蒙PC专项积分赛-依赖。当前完整验证 run 为 libwebp-1.6.0.2-finish-step5-20261011-r004，测试候选 tree 为fe03e66cfb341f8f40bf7e4236df857756d5318b。配方仅在 OHOS 路径配置真实 Clang 与签名工具，非 OHOS 保留 Conan toolchain；recipe SHA256 5c01bbe198dc2735f6af6bfc426e311692a503004a80e0d384bb6e04e658e199，签名入口 SHA256 aa57a1b7edda87f7026ef12b16cebd8b429f6c859bdfdde6d179bd2f2d447fca。测试后仅刷新正式生成证据、元数据及正文，运行输入保持测试时字节。探索结果、旧事务和旧 PR #13623 的 Review/CI 不冒充当前 HEAD 门禁。

当前正式同run证据：`reports/official-step35-observed.json` SHA256 `fee4ab8d0f1d46496c0a35e5fc4f4fbb410d586519c05208e99496f357d70762`；`reports/upstream-source-cases-observed.json` SHA256 `159943bf4afdf7abbe085de9ae4239f65e63b349a13598f6217b0cfd0825106d`。r004 原 setup/build_and_test 和官方 step35 实际 RC0，Conan create、原76项、消费者4项、鸿蒙1项均通过。官方生成的结果按原字节保存在本地，不纳入 Git；不手工制造或修改结果文件。完整 WAL/receipt 哈希链、唯一 launch、release/postrelease、自有进程0和清理后工作根不存在已独立核对。历史失败与旧证据全部保留，不将本地 CI 冒充平台 CI。

---

## 补充说明

观察 SHA 字节集：任务原始 CRLF 副本为9c44182d456b890bf788d9c0dc151320809ee11c9ce2bf11902f0dfb9c27cd0d（48727字节）及10f3be25105582c22a1c8db1c3571a8960e4ea67e8f3487658a3186061a69025（7839字节）；仓内 Git LF blob 为d248ac7cb328d2a55fe40a8676f6d0934335c6bd73ef7d3fb3283de6e45326ac及b46560f37ff58aabde82889ca9eba41ae7b03694ab0c80daae153d8adb14dfd3，JSON 值一致。没有重写旧 observer/receipt 或剔除自指字段。

- 关联 Issue：[Issue #3565](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3565)，已权威回读为本账号唯一 OPEN 的真实1.6.0.2修复申请；当前唯一关联为 [PR #14954](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/14954)。真实任务14927已领取；知识编号纠正后的当前候选仍须重新通过 POST_CREATE，不复用旧 HEAD 合同。
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：fix/libwebp-1.6.0.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：此为真实更高修复版本，修复旧配方禁用原测试、缺少鸿蒙专项以及未知平台 C++ 标准/ELF 链接行为；不是同版本重复导入。知识草稿配对提交并重新绑定当前候选门禁。平台 Review/CI 已在旧 HEAD 触发；知识编号纠正后以新 HEAD 的实际 Review/CI 为准，不把未领取或未完成的 CI 请求当作通过，也不冒称已提审。
