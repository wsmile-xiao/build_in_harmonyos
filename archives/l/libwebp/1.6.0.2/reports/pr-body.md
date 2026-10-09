## PR 信息

- **三方库名称**：libwebp
- **上游版本**：官方 1.6.0；本次适配修复版本 1.6.0.2，不冒称新上游标签
- **上游仓库地址**：https://github.com/webmproject/libwebp
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）；已按当前完整证据逐项重判HD1—HD4，四项均未匹配
- **使用知识库**：E096、E130；本次实质增量配对草稿 E2026100907-draft-LWP2。旧 E696 已被主线其他贡献占用，本次只迁移本 PR 草稿对，保留他人条目不变。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 64 | 官方固定 ANTLR 4.12.0 默认启用原用例，原参数化 IDs 分别 32+32；不关闭 BUILD_TESTING |
| 集成测试 | 12 | 官方 libwebp 1.6.0 原 tests/fuzzer 入口，含原基础 7、mux 4、info 1；执行其固定 FuzzTest harness，非只统计注册 |
| 其他测试 | 0 | 该原 CMake 路径未发现独立额外运行入口；精确清单与源审计将附正式证据 |
| **合计** | **76** | 正式 Conan r006、官方 step35 r002 分别在各自同一事务实际 76/76、零 skip，独立源码 IDs 和 ANTLR 原参数核对通过；不拼跨run分母 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 64 | 不变 | 原 ANTLR 测试与断言未修改；仅构建平台能力探测修复 |
| 集成测试 | 16 | +4 | 原 libwebp 12；另有消费者真实无损 RGBA、元数据 mux/demux、有损尺寸/alpha 和坏码流拒绝 4 项 |
| 鸿蒙特有测试 | 1 | 新增 | HarmonyOS PC AArch64 ELF codesign、实际 SONAME/NEEDED 与自有包运行时命名空间、真实 codec 调用的独立专项 |
| **合计** | **81** | **+5** | 正式 Conan r006 与现行官方本地 CI r002 各自同一事务实际 76+4+1 全通过，不拼跨run分母 |

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

2026-10-09 后续整改：完整 AtomCode 报告192792991已公开，真实非OHOS编译器覆盖问题已修复。新候选分别通过 fresh 正式 Conan r006 和官方 FinishPipeline.step35_local_ci r002，原测试、消费者、鸿蒙专项均在各自同run真实执行。上述为本地/真机验证，不是平台 CI；推送后仍以当前完整 HEAD 的最新 Review 和平台 CI 为准。

本文件为 PR #14954 的六节正文。Issue #3565 与本 PR 双向唯一关联，真实修复任务14927（libwebp1.6.0.2，fix/libwebp-1.6.0.2）已领取，账号2301_80739235，活动为开源鸿蒙PC专项积分赛-依赖。正式证据绑定实际配方、完整 HEAD/tree、唯一 run、boot/UID、输入 SHA-256、真实 stdout/stderr/RC、原 source case IDs 和完整 WAL/receipt 链。修复配方仅在 OHOS 路径配置实际 Clang 与签名工具，非 OHOS 保留 Conan toolchain 的编译器选择；新 recipe SHA256 为5c01bbe198dc2735f6af6bfc426e311692a503004a80e0d384bb6e04e658e199。新事务测试候选tree为1f561d3e25f7cc1bcb759ecdb074f1fe13e7bbe0，后续仅刷新真实证据与正文，运行输入不变。探索结果和旧 PR #13623 的 Review/CI 不冒充当前 HEAD 门禁。

正式同run证据：libwebp-conan-observed-r006.json SHA-256 `5c588d5b0433e6c63c7f2d74b7fb2fd12ba5debd522b4a60d404358e947468d2`；libwebp-conan-source-cases-observed-r006.json SHA-256 `0c1c62564b2b2f539c51fe397357036b090f2fbc91c3d25df30c60242b6c7cc4`。官方step35 r002原setup/build_and_test RC0、76+4+1和L0/L1通过；新`.ci-result.json`实际由官方方法生成、原日志SHA `1cff1cf7b5315e96fd1ca0d02434f99b1c0802220d0fe82c0c570da3d7871b8d`独立核对。`reports/official-step35-observed.json` SHA `b7cf658765973d34eb27d4f8048f2b5f5f24ab3cca1179895a68ff8acd304bb1`、`reports/upstream-source-cases-observed.json` SHA `25a16a8f75bbe09397893264394d31c9fc55c103235a7d12c24d1031a1f5be65`。各run唯一launch/release/postrelease/自有进程0均独立核对；旧证据全部保留，不将本地CI冒充平台CI。

---

## 补充说明

观察 SHA 字节集：任务原始 CRLF 副本为9c44182d456b890bf788d9c0dc151320809ee11c9ce2bf11902f0dfb9c27cd0d（48727字节）及10f3be25105582c22a1c8db1c3571a8960e4ea67e8f3487658a3186061a69025（7839字节）；仓内 Git LF blob 为d248ac7cb328d2a55fe40a8676f6d0934335c6bd73ef7d3fb3283de6e45326ac及b46560f37ff58aabde82889ca9eba41ae7b03694ab0c80daae153d8adb14dfd3，JSON 值一致。没有重写旧 observer/receipt 或剔除自指字段。

- 关联 Issue：[Issue #3565](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3565)，已权威回读为本账号唯一 OPEN 的真实1.6.0.2修复申请；当前唯一关联为 [PR #14954](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/14954)。真实任务14927已领取；知识编号纠正后的当前候选仍须重新通过 POST_CREATE，不复用旧 HEAD 合同。
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：fix/libwebp-1.6.0.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：此为真实更高修复版本，修复旧配方禁用原测试、缺少鸿蒙专项以及未知平台 C++ 标准/ELF 链接行为；不是同版本重复导入。知识草稿配对提交并重新绑定当前候选门禁。平台 Review/CI 已在旧 HEAD 触发；知识编号纠正后以新 HEAD 的实际 Review/CI 为准，不把未领取或未完成的 CI 请求当作通过，也不冒称已提审。
