## PR 信息

- **三方库名称**：libxft
- **上游版本**：2.3.9
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxft
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E077、E2146，以及本 PR 的 E2164、E2165 配对知识草稿

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 2.3.9 release 未注册单元测试 |
| 集成测试 | 0 | Meson 没有 `test()` 注册，Automake 兼容入口也为空 |
| 其他测试 | 0 | `meson test` 报告 `No tests defined` |
| **合计** | **0** | 完整源码盘点记录为 `INVENTORY_COUNT=0` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 上游没有可保留的独立单元测试 |
| 集成测试 | 2 | +2 | 两个独立 Conan 消费者程序，分别覆盖 API surface 和 name contract |
| 鸿蒙特有测试 | 0 | 不变 | OHOS/arm64 是真实执行平台，不把同一消费者重复计数为额外用例 |
| **合计** | **2** | **+2** | 2/2 程序通过；79 + 16 = 95 assertions |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 2.3.9 未注册测试，本 PR 未修改上游源码或测试。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 新增 `libxft_api_surface` 和 `libxft_name_contract` 两个独立消费者。前者绑定 77 个公开函数并验证版本和 FreeType 初始化，后者覆盖 Fontconfig name 与有效/无效 XLFD 合同。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：2/2（100%）
- fresh W0：12/12 依赖节点完整，五个直接 binary 实际取回，`Missing=0`、`info_invalid=0`。
- fresh W3：`libxft-2.3.9-w3-r26-21c8cbbf` 在 `10.62.148.108:2222` 单次 launch 通过，shared/static variants 4/4，95 assertions，release 与两次 clean scan 通过。
- official finish：Conan verify、Conan create、两个 test_package 消费者和生成的 `.ci-result.json` 均通过；聚合 RC1 仅来自 W3 后的全局知识基线和旧式 `packaging/` 检查，按 `PARTIAL_POST_W3` 保留原始证据。

---

## 补充说明

- 关联 Issue：#2383
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/libxft-2.3.9
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：本库是 Issue #1272 `spatialite-gui/2.1.0-beta1` 的真实传递依赖。E2164 与 E2165 解决两类跨库可复用问题；PR 验证不上传 Conan/CNB 制品，正式发布只在合并后由 release 流水线执行。
