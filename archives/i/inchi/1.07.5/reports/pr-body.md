## PR 信息

- **三方库名称**：inchi
- **上游版本**：v1.07.5
- **上游仓库地址**：https://github.com/IUPAC-InChI/InChI
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E2175（本 PR 配套知识草稿）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 7 | 上游 CTest/GoogleTest 可执行程序清单，见 `reports/upstream-inventory.txt`；共报告 59 个 runtime case |
| 集成测试 | 0 | 上游清单未包含独立集成测试入口 |
| 其他测试 | 0 | 上游清单未包含其他测试入口 |
| **合计** | **7** | `INVENTORY_COUNT=7`，7 个程序全部执行并通过 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 7 | 不变 | 上游 7 个程序，runtime case 59/59 |
| 集成测试 | 1 | +1 | Conan consumer 链接 `inchi::inchi` 并执行 6 项 API 断言 |
| 鸿蒙特有测试 | 0 | 不变 | 目标平台签名、ELF 和 release/postrelease 属于 W3 状态验证，不另列测试入口 |
| **合计** | **8** | **+1** | 上游清单与 consumer 结果见 `reports/test-report.md` |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游测试源保持原样；仅通过 Conan 配方启用 `BUILD_TESTING=ON` 并链接已发布的 gtest。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 `test_package/test_inchi.c` 是独立的 Conan 包消费者集成测试，覆盖公开 C API 的有效/无效 InChI 分类、InChIKey 生成与校验；它不是对上游测试缺口的补全，也不是对上游测试源的修改。目标 consumer 为 1/1，API 断言为 6/6。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：7/7（100%）
- 新增测试用例通过率：1/1（100%）

交叉构建完成 132 个编译/链接步骤；产物为 AArch64 ELF，无 RPATH/RUNPATH 和路径型 NEEDED。W3 `inchi-1.07.5-w3-r4` 在 `10.62.150.125:8022` 唯一 launch 后完成 consumer 1/1、API 6/6、上游 7/7、runtime 59/59、signed state 10/10、release/postrelease PASS；事务结果 SHA-256 为 `01809a9efb0dd322b2ea0f6a87ed21c0659fba8b84e67da58f0df9641681199e`。

---

## 补充说明

- 关联 Issue：#2631
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/inchi-1.07.5
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：知识查重覆盖 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations`，结论为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`；E2175 总结 Windows Conan/CMake/Ninja 多层 flag 序列化时保持单一 sysroot argv 边界的通用方法。依赖 `gtest/1.17.0` 已从 `ohpcd` 以 `--build=never` 解析，发布动作保留为合并后的 `/release`，本 PR 不上传制品。
