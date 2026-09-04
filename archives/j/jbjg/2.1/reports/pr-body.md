## PR 信息

- **三方库名称**：jbjg（JBIG-KIT）
- **上游版本**：2.1
- **上游仓库地址**：https://www.cl.cam.ac.uk/~mgk25/jbigkit/
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E2174-draft-2301（本 PR 配套草稿）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 2 | `libjbig/Makefile` 的 `tstcodec` 与 `tstcodec85` |
| 集成测试 | 0 | 上游归档无独立集成测试入口 |
| 其他测试 | 0 | 上游归档无其他测试入口 |
| **合计** | **2** | 清单见 `evidence/upstream-test-inventory.txt` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 2 | 不变 | r4 `make all check` 完整执行 T.82/T.85 |
| 集成测试 | 1 | +1 | Conan `test_package` 通过 CMakeDeps 链接并运行 |
| 鸿蒙特有测试 | 0 | 不变 | 无新增平台专属测试；目标机运行作为平台验证 |
| **合计** | **3** | +1 | 上游清单与消费者证据见任务 evidence |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：2/2（100%）
- 新增测试用例通过率：1/1（100%）

目标机 W3 r4 的正式 `conan create` 返回 RC 0；两个上游套件和真实
`jbg_dec_init/free` 消费者测试均通过。r3 的失败由 `check` 未依赖库归档
目标引起，r4 以 `all check` 修复。Windows 本地 `make -C` 仅作为诊断时
受 MSYS 路径语义限制，未替代目标机证据。

---

## 补充说明

- 关联 Issue：#2564（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2564）
- 队伍名称：OpenHarmony PC Contributors
- 申请人显示标识：2301_80739235
- 源分支：OpenHarmonyPCDeveloper:feat/jbjg-2.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：本 PR 新增 E2174 配套知识草稿对，结论适用于手写 Makefile
  的产物目标与测试目标分离场景；r4 payload SHA-256 为
  `4d76d8540f3177967dd00d5bf21ab801d3792493baddeffc116a99545d0c209d`。
