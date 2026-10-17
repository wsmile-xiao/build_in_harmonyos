## PR 信息

- **三方库名称**：qrencode
- **上游版本**：v4.1.1
- **Conan 修订版本**：4.1.1.1（4.1.1 已被制品仓中的不同 recipe 占用）
- **上游仓库地址**：https://github.com/fukuchi/libqrencode
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E2175（本 PR 新增草稿，固定可选 CMake 后端后核对 CTest 分母）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 12 | 来源：上游 `tests/`，由 OHOS W3 runner manifest 与同一事务日志盘点 |
| 集成测试 | 0 | 上游 v4.1.1 未定义独立集成测试组 |
| 其他测试 | 0 | `WITH_TOOLS=OFF`、`WITHOUT_PNG=ON` 后无额外工具测试 |
| **合计** | **12** | 清单证据：`F:\HarmonyPC\miniupnpc-2.3.11-adapt-20260904\upstream-inventory-qrencode-4.1.1.txt` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 12 | 不变 | OHOS 真机完整执行 `test_bitstream` 至 `test_rs` |
| 集成测试 | 1 | +1 | Conan `test_package` 消费者调用真实 `QRcode_encodeString` API |
| 鸿蒙特有测试 | 0 | 不变 | 无额外平台专属测试组 |
| **合计** | **13** | **+1** | 上游 12/12，消费者 1/1 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游 `tests/` 目录保持原样；仅在配方中固定构建开关并调用上游测试入口。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

Conan `test_package` 是消费者契约测试，不是对上游缺失测试的替代；它额外验证安装后的公共 API、矩阵数据和释放流程。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：12/12（100%）
- 新增测试用例通过率：1/1（100%）

### 本地构建与 CI 模拟

- `build_and_test.sh archives/q/qrencode/4.1.1.1`：L0、KC、JC、Conan create、消费者 `test_package`、L1、L4、L5 全部通过；L2 因库无 `bin/` 目录按规则跳过。
- 本地 Conan 上游 CTest：3/3 PASS（`test_bitstream`、`test_estimatebit`、`test_split`）；消费者测试 1/1 PASS。
- `.ci-result.json` 由本轮 finish 在 `2026-09-04T20:41:48.640726` 生成，绑定 `qrencode/4.1.1.1`、当前归档绝对路径和 `exit_code=0`，完整性哈希为 `a88ca8cad5a54964`。

### OHOS 真机 W3

- 历史等价事务：`qrencode-4.1.1-w3-20260904-004`，唯一 launch，目标 `10.62.150.125:8022`；该证据属于上游 4.1.1 同源码，不冒充 4.1.1.1 新事务。
- boot ID：`068fec8d-10f6-40f7-93a6-9153e0ad6d33`；runner 清零，release/postrelease PASS。
- 上游 12 个测试程序全部 `TEST_RC 0`，消费者测试 `QRcode_encodeString` 返回 21x21 矩阵并通过：12/12 + 1/1。
- 真机原始日志 SHA-256：`b98daeb1b9ad64a4b91ffb525acae6a0ac2a08f2d24247df0d92ddf8b5d2e69b`。

### 适配说明与限制

- `WITH_TESTS=ON`、`WITH_TOOLS=OFF`、`WITHOUT_PNG=ON` 写入 CMakeToolchain；`CMAKE_POLICY_VERSION_MINIMUM=3.5` 处理上游旧 minimum。
- 默认静态库交付；PNG 输出和工具需要显式开启对应选项及依赖，不能把默认构建结果解释为 PNG 能力。
- 本 PR 未修改上游源码，也未新增运行时依赖。

---

## 补充说明

- 关联 Issue：#2642（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2642）
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/qrencode-4.1.1.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：CI 首次运行发现 `qrencode/4.1.1` 已被不同 recipe 占用，按 R37 迁移到连续修订 `4.1.1.1`；Issue/PR 标题和正文同步该修订号，分支精确使用 `feat/qrencode-4.1.1.1`。历史 W3 仅作同源码功能等价证据；新修订必须先通过平台 CI 才提审。
