## PR 信息

- **三方库名称**：libxml2-utils
- **上游版本**：v2.15.3
- **上游仓库地址**：https://github.com/GNOME/libxml2/releases/tag/v2.15.3
- **适配路径**：路径 A（基础适配）+路径 B（贡献创新）
- **使用知识库**：E564-draft-2301_80739235；ohos-elf-native-signer-selfsign；w3-hmdfs-file-owner-permission-before-launch

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 22 | CTest 清单见 `archives/l/libxml2-utils/2.15.3/reports/upstream-test-inventory.txt`，含 `INVENTORY_COUNT=22` |
| 集成测试 | 0 | 上游本轮入口未单独注册集成测试 |
| 其他测试 | 0 | 上游本轮未单独注册其他测试 |
| **合计** | **22** | `ctest --test-dir upstream-host-build --output-on-failure --parallel 2` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 22 | 不变 | 上游 CTest 22/22 PASS |
| 集成测试 | 0 | 不变 | 无新增集成入口 |
| 鸿蒙特有测试 | 1 | 新增 | 目标机 native self-sign 的 xmllint/xmlcatalog runner，W3 run-002 真实执行 PASS |
| **合计** | **23** | **+1** | 清单见上游和 HarmonyOS 专属测试报告 |

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
- 上游测试用例通过率：22/22（100%）
- 新增测试用例通过率：0/0（不适用）

鸿蒙特有测试为独立硬门禁：`HARMONY_TEST_COUNT=1`，W3 run-002 在 `10.62.150.125:2222` 完成唯一 launch、目标读写执行校验、cleanup/postrelease，结果为 `W3_RESULT=PASS`。

其他证据：Conan host=`OHOS/armv8`、build=`Windows/x86_64`，G2/G3/G4/L2/L4/L5 PASS；本地 CI overlay 1/1 PASS（L0/L1/L1e/L4/L5 PASS，L2 按交叉编译合同跳过）；当前 HEAD 为 `a675263b91fd9cef49cbce7aafb54062ae10df2c`。

---

## 补充说明

- 关联 Issue：#3004
- 队伍名称：开源鸿蒙PC专项积分赛-依赖
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/libxml2-utils-2.15.3
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：W3 run-001 的 HMDFS RC126 保持为不可变失败证据；run-002 通过 native self-sign 和有效用户 `test -r`/`test -x` 校验后 PASS。E564 草稿对记录该平台边界；Issue #3004 的 PRE_CREATE 关联区为“PR：待创建 / PR 链接：待创建 / 当前状态：待创建”。
