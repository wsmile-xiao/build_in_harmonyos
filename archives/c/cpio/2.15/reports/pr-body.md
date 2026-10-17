## PR 信息

- **三方库名称**：cpio
- **上游版本**：2.15
- **上游仓库地址**：https://www.gnu.org/software/cpio/
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E2181（本 PR 草稿）；autoconf-config-guess-task-local-compiler-tuple；ohos-elf-native-signer-selfsign；potential-simple-w0-binary-closure-gate

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游 testsuite 未按单元测试拆分 |
| 集成测试 | 17 | `validation/upstream/tests.log` 的 `make -C tests check` 清单 |
| 其他测试 | 0 | 无额外上游测试入口 |
| **合计** | **17** | `archives/c/cpio/2.15/reports/upstream-inventory.txt`，INVENTORY_COUNT=17 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 未新增单元测试 |
| 集成测试 | 17 | 不变 | 上游 Autotest 保持原样并通过 |
| 鸿蒙特有测试 | 3 | +3 | 目标机 version、newc 创建、newc 解包闭环 |
| **合计** | **20** | +3 | `w3-r2/launch-output.txt` 与 WAL 的 target_functional_smoke 3/3 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游 `tests/` 测试源和测试入口未修改；目标机 smoke 独立于上游测试目录。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游已有完整 Autotest 覆盖；新增仅是目标平台可执行性和归档往返边界验证。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：17/17（100%）
- 新增测试用例通过率：3/3（100%）

官方源码归档 SHA-256 为 `EFA50EF983137EEFC0A02FDB51509D624B5E3295C980AA127CEEE4183455499E`。OHOS 交叉编译产物为 AArch64 PIE，动态依赖仅 `libc.so`；本地消费者归档创建/解包断言 6/6。真机 W3 run `cpio-2.15-w3-20260904-r2` 在 `10.62.150.125:8022` 完成双次精确传输、native self-sign、唯一 launch，target smoke 3/3，结果 `W3_RESULT=PASS`，release/postrelease 为 `REMOTE_ROOT_ABSENT`。

---

## 补充说明

- 关联 Issue：#2647
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/cpio-2.15
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：依赖任务 #5979；新增 E2181 配对草稿，记录旧版 Autotools OHOS 三元组与 Windows 挂载权限测试边界。候选 HEAD 为 `fda3ca5e0c787e9783d60e2e5e8451a4a7ca8ca6`，W3 r2 证据不跨 run 拼接；平台 CI 通过后才触发一次 AI Review，Review 终态无阻塞意见后再提审。
