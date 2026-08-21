## PR 信息

- **三方库名称**：libxext
- **上游版本**：1.3.7
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxext
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新） / 路径 C（高难度挑战）
- **使用知识库**：E331-draft-2301；conan-libtool-transitive-la-shadow-closure；finish-w3-substep-postw3-readiness-boundary

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | release 的 Makefile.am 未声明 TESTS 或 check_PROGRAMS |
| 集成测试 | 0 | release 未注册 check-local 或其他测试入口 |
| 其他测试 | 0 | `make -j1 check` 存在但执行清单为空 |
| **合计** | **0** | 冻结清单证据记录 `INVENTORY_COUNT=0` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 上游未提供独立单元测试入口 |
| 集成测试 | 2 | +2 | installed-package XSync 与 extension registry consumers |
| 鸿蒙特有测试 | 0 | 不变 | 两个消费者均验证公共、跨平台 API，无平台条件跳过 |
| **合计** | **2** | **+2** | normal 与 forced-static 变体均完整通过 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

未修改上游测试源码；release 本身没有注册可执行测试项。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：新增 2 个 installed-package integration consumers。
- **补全原因**：上游 release 的 `make check` 清单为零，需要验证安装后头文件、链接接口和运行时 API 合同。
- **新增测试文件清单**：
  1. `archives/l/libxext/1.3.7/test_package/sync_value_contract.c` - 验证 16 个 display-independent XSync value API。
  2. `archives/l/libxext/1.3.7/test_package/registry_contract.c` - 验证 extension registry 生命周期和 error handler round-trip。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：2/2（100%）
- Fresh isolated OHOS/arm64 W0：8/8 依赖节点均有 RREV/PID/PREV，`binary_remote=ohpcd`，`info_invalid` 为空。
- Exact-snapshot W3：normal 2/2、forced-static 2/2，官方 `.ci-result.json` 的 `exit_code=0`。
- 完整 `finish`：`PARTIAL_POST_W3`，仅后置 `step5b`、`step8`；未将聚合 RC 1 改写为完整 PASS。

---

## 补充说明

- 关联 Issue：#1957
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/libxext-1.3.7
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：这是 OpenJ9 0.59.0 的真实前置依赖；旧 `1.7.0` publication fact 保留在 manifest 中，并标记为 invalid/non-superseding，其无效上游身份不参与稳定版本 supersession。PR 合并后的正式 release 与 fresh registry readback 仍是独立后置门禁。
