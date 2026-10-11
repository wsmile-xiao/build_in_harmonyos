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
| **合计** | **76** | 当前候选在官方 step35 r006 同一事务实际 76/76、零 skip；逐项核对原 FuzzTest IDs 和 ANTLR 原参数，不拼跨run分母 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 64 | 不变 | 原 ANTLR 测试与断言未修改；仅构建平台能力探测修复 |
| 集成测试 | 16 | +4 | 原 libwebp 12；另有消费者真实无损 RGBA、元数据 mux/demux、有损尺寸/alpha 和坏码流拒绝 4 项 |
| 鸿蒙特有测试 | 1 | 新增 | HarmonyOS PC AArch64 ELF codesign、实际 SONAME/NEEDED 与自有包运行时命名空间、真实 codec 调用的独立专项 |
| **合计** | **81** | **+5** | 当前修复候选在官方本地 CI r006 同一事务实际 76+4+1 全通过，不拼跨run分母 |

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

### 当前验证权威（2026-10-11，r006）

本次实际修复签名原生装载器捕获失败输出却未向 CI 传播的问题：保留原 argv、120 秒超时、check=True、原异常与退出码，将真实子进程 stdout/stderr 和非零返回码输出后重新抛出同一异常。真实子进程 exit7 正负定向验证 2/2，不用 mock 替代运行结果。

fresh 唯一事务 `libwebp-1.6.0.2-finish-step5-20261011-r006`，父 HEAD `50a9949b3e60e788ebf5234c1fdc310235301920`，实际暂存测试 tree `a7565e8d6933b00a88643ac072ac06d118a73f2c`：官方 step35、干净 Conan create 均真实 RC0，原上游 76/76、消费者 4/4、鸿蒙专项 1/1，零失败/跳过。独立观察 SHA256 `3e480e02ac65adbc42fb933508be13ccfc33e5dc2651d66b6702454c744434d1`，逐源码观察 SHA256 `7eb67685a4a2c95a6fe0e8862f423c15dc1ae5a2b45ac45d030359745c97bcec`，完整官方日志 SHA256 `f49b1132a4c99983b780c6147ee47f0468fa9e2dff2ec78128c5c9114583dd37`。

完整 WAL/receipt 链、唯一 launch、自有进程清零、release/postrelease 已独立核验。仅此 r006 绑定当前运行输入；后续提交只是报告和配对知识更新，完整新 HEAD 的平台 Review/CI 另行权威回读。下列 r005/r004 与更早文字均为保留的历史记录，不得作为当前验证权威或平台 CI 通过证明。实际原始 Harmony/W3 输出与 Git 投影字节集均见当前证据索引，历史投影不会被解释为第二次执行。

**当前验收更新（2026-10-11，r005）**：平台 build96229 的原上游及消费者通过，但原 Python ctypes 鸿蒙探针对私有已签名 DSO 返回 Permission denied。现改为独立签名、未预链接被测库的原生 ELF 探针：保留 ELF64/AArch64/签名/SONAME/NEEDED 校验，真实 dlopen/dlsym、同包依赖预加载、RGBA 编解码和 dladdr/maps 包归属断言。库不承诺 Python ctypes 绑定；该调整验证原生库能力，不声称 ctypes 的具体系统策略故障已解决。原失败证据保留，未用 stub、系统替代库或跳过代替专项。

新 run `libwebp-1.6.0.2-finish-step5-20261011-r005`、测试 tree `37d65b023c7ddb8c9d1ba667af99a8275c81b2ba` 中，官方 FinishPipeline.step35_local_ci 实际干净 Conan 构建、原76/76、消费者4/4、鸿蒙1/1均通过，零失败/跳过。独立观察SHA `34bf8d447dc79944adce78e45bf86d0004e4ec5950e65fc723a46bebd99b36c0`；逐源码 ID/ANTLR 原参数观察SHA `27c6c6de9d0e4d6cf910074a41181a4d07aa341cbcc05a0d98f4c7bf29be0d5d`。完整回执链、唯一 launch、release/postrelease、自有进程0已核验。以下 r004 段落及旧哈希是保留的历史验证，不覆盖当前 r005；本地成功不是当前新 HEAD 平台 CI、Review 或提审成功。

2026-10-11 后续整改：真实 AtomCode 检视发现签名入口的格式边界和测试树元数据问题。严格签名模式现在拒绝短头、错误 magic、ELF32、大端以及非执行/共享对象；编译器包装器区分 -c/-S/-E/-fsyntax-only 纯编译动作，不要求签名合法的 ET_REL 对象，真正链接仍保留签名及非零退出失败传播。直接把所有 ET_REL 都判为失败会破坏上游编译探测，因此没有采用这一错误修法。MANIFEST 动态路径与真实 Conan 参数绑定。本机定向12/12后，fresh 官方 FinishPipeline.step35_local_ci r004 实际干净 Conan 构建及76+4+1同run全通过。完整28文件的真实检视报告SHA256为0a5bdc13e322d032c9fb0601e8be5dd881c5cc4169af59790d0fa9a9e34e41bf，公开报告及处置说明为评论193169907；两个大型原始日志仅哈希绑定摘录，该检视不冒充完整逐行日志审核。新提交后另行回读该完整HEAD评审与平台CI。

本文件为 PR #14954 的六节正文。Issue #3565 与本 PR 双向唯一关联，真实修复任务14927（libwebp1.6.0.2，fix/libwebp-1.6.0.2）已领取，账号2301_80739235，活动为开源鸿蒙PC专项积分赛-依赖。当前完整验证 run 为 libwebp-1.6.0.2-finish-step5-20261011-r004，测试候选 tree 为fe03e66cfb341f8f40bf7e4236df857756d5318b。配方仅在 OHOS 路径配置真实 Clang 与签名工具，非 OHOS 保留 Conan toolchain；recipe SHA256 5c01bbe198dc2735f6af6bfc426e311692a503004a80e0d384bb6e04e658e199，签名入口 SHA256 aa57a1b7edda87f7026ef12b16cebd8b429f6c859bdfdde6d179bd2f2d447fca。测试后仅刷新正式生成证据、元数据及正文，运行输入保持测试时字节。探索结果、旧事务和旧 PR #13623 的 Review/CI 不冒充当前 HEAD 门禁。

当前正式同run证据：`reports/official-step35-observed.json` SHA256 `fee4ab8d0f1d46496c0a35e5fc4f4fbb410d586519c05208e99496f357d70762`；`reports/upstream-source-cases-observed.json` SHA256 `159943bf4afdf7abbe085de9ae4239f65e63b349a13598f6217b0cfd0825106d`。r004 原 setup/build_and_test 和官方 step35 实际 RC0，Conan create、原76项、消费者4项、鸿蒙1项均通过。官方生成的结果按原字节保存在本地，不纳入 Git；不手工制造或修改结果文件。完整 WAL/receipt 哈希链、唯一 launch、release/postrelease、自有进程0和清理后工作根不存在已独立核对。历史失败与旧证据全部保留，不将本地 CI 冒充平台 CI。

---

## 补充说明

当前证据索引为 `reports/current-runtime-evidence-binding.json`；旧 `raw-log-evidence-index.json` 明确保留为 r001 历史记录。r005 的原 Harmony 输出为486658字节、SHA256 `0e2c7d11e6da1e3c090e0f05a1d59b388be835b5a6c350e8ab8466075ecabab7`；原完整 W3 输出为488182字节、SHA256 `d5b818abed9662d11437592c7f07e406a98a27ec6ad8083078353291f77308a0`。仓内两份 log 路径均投影同一完整 W3 输出，这是既有表格兼容别名，不代表两个独立测试或原 Harmony 输出。检视包装器曾对文本 `.strip()`，导致摘录摘要丢失终止换行；独立按 Git 原始 blob 字节重算后与原 W3 哈希一致，未修改原日志或回执。

原生 r005 验证的是暂存候选 tree `37d65b023c7ddb8c9d1ba667af99a8275c81b2ba`，其父 HEAD 为2232c1f4；不是以父 HEAD 冒称运行候选。提交 b1b9058b 相对此测试 tree 仅有报告和知识草稿差异，实际13个运行输入逐字节相同；本次仅修正 manifest/索引/正文的陈旧标注，不改变配方、源码、补丁、消费者或鸿蒙测试。完整静态检视的解码链接意见经官方 CMake 源码核对：`webp` 自身包含 `webpdecode` 对象及 `WebPDecodeRGBA`，`webpdecoder` 是独立解码-only选择，不是 `WebP::webp` 的必需依赖。保留当前真实 API 消费者及同run4/4证据，不因误报新增链接。

以下 r004 run/tree 及更早字节集段落均为历史记录；当前验证权威是上面的 r005 和索引。新提交后的完整 HEAD、Review、CI 由平台权威回读绑定，不把历史成功迁移为新 HEAD CI。

观察 SHA 字节集：任务原始 CRLF 副本为9c44182d456b890bf788d9c0dc151320809ee11c9ce2bf11902f0dfb9c27cd0d（48727字节）及10f3be25105582c22a1c8db1c3571a8960e4ea67e8f3487658a3186061a69025（7839字节）；仓内 Git LF blob 为d248ac7cb328d2a55fe40a8676f6d0934335c6bd73ef7d3fb3283de6e45326ac及b46560f37ff58aabde82889ca9eba41ae7b03694ab0c80daae153d8adb14dfd3，JSON 值一致。没有重写旧 observer/receipt 或剔除自指字段。

- 关联 Issue：[Issue #3565](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3565)，已权威回读为本账号唯一 OPEN 的真实1.6.0.2修复申请；当前唯一关联为 [PR #14954](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/14954)。真实任务14927已领取；知识编号纠正后的当前候选仍须重新通过 POST_CREATE，不复用旧 HEAD 合同。
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：fix/libwebp-1.6.0.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：此为真实更高修复版本，修复旧配方禁用原测试、缺少鸿蒙专项以及未知平台 C++ 标准/ELF 链接行为；不是同版本重复导入。知识草稿配对提交并重新绑定当前候选门禁。平台 Review/CI 已在旧 HEAD 触发；知识编号纠正后以新 HEAD 的实际 Review/CI 为准，不把未领取或未完成的 CI 请求当作通过，也不冒称已提审。
