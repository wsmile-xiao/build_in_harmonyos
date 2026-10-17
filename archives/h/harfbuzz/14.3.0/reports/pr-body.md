## PR 信息

- **三方库名称**：harfbuzz
- **上游版本**：14.3.0
- **上游仓库地址**：https://github.com/harfbuzz/harfbuzz
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；E2153-draft-2301-conan-package-folder-materialization（随本 PR 提交）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 22 | 来源：Meson `src` 测试目标 `test-algs` 至 `test-unicode-ranges` |
| 集成测试 | 2 | 来源：`shape_threads`、`subset_threads` |
| 其他测试 | 51 | 7 个源码/符号检查、1 个 release-notes 检查、43 个 fuzzing chunk |
| **合计** | **75** | `intro-tests.json` 清单与 JSONL 终态按唯一名称和顺序严格配对 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 22 | 不变 | 完整执行上游单元测试 |
| 集成测试 | 3 | +1 | 2 个上游线程/慢速入口，加 1 个 shared Conan 消费者流程 |
| 其他测试 | 51 | 不变 | 7 个源码/符号检查、1 个 release-notes 检查、43 个 fuzzing chunk |
| 鸿蒙特有测试 | 0 | 不变 | 平台行为由同一上游清单和包验证门禁覆盖，不重复计数 |
| **合计** | **76** | **+1** | 上游 75 项加真实消费者 1 项；9 个消费者断言不拆分计数 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

未修改或排除上游测试源码。配方仅绑定可执行 Python 解释器，并在执行原始 Meson 测试命令前物化已签名的共享库别名。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增的 Conan 消费者属于安装包集成验证，不是用来替代上游测试。它通过 `harfbuzz::harfbuzz` 链接 shared 包，验证 14.3.0 版本、`Harmony` 塑形结果和 14.3.x `hb_ot_fetch_number` API。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：75/75（100%）
- 新增测试用例通过率：1/1（100%）

- OHOS/arm64 W3：`20260819T010115Z`，设备 `currentUser@10.62.215.229:2222`
- W0：`freetype/2.14.3` 完整 RREV/PID/PREV，`binary_remote=ohpcd`，`info_invalid=0`，missing=0
- shared 包：HarfBuzz RREV `d95aa2283a886e19705accd5a38c7aa9`，PID `02e364f2d646dda8acabc40d95696553e6e53235`，PREV `1ac65b51d4fb18288f6913c88114e961`
- 消费者终态：`harfbuzz 14.3.0 shaping and fetch APIs: PASS (7 glyphs)`
- 上游原始结果：75 个唯一 Meson JSONL 终态全部 `OK`/RC0，失败 0，跳过 0
- r4、r5、r6 的配置、共享库加载和验证器失败均保留在 `notes.md`，未改写为通过

---

## 补充说明

- 关联 Issue：#2278
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/harfbuzz-14.3.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- contrib 任务：3712；精确任务行是所有权权威，#1866 仅作关联追踪
- 知识查重：最新 main 的四个规定范围未发现与“graph 身份解析和 install 包目录物化按 RREV/PID/PREV 连接”语义等价的条目
- 发布边界：合并前不执行 `/release`；合并后发布仍须由全新隔离 Conan home 的 download、graph info、install `--build=never` 回读证明
