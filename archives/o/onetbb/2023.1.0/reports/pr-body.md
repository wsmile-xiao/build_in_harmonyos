## PR 信息

- **三方库名称**：onetbb
- **上游版本**：v2023.1.0
- **上游仓库地址**：https://github.com/uxlfoundation/oneTBB
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E2184-draft-2301_80739235；E7003-draft-2301_80739235；E7004-draft-2301_80739235；E2182-draft-2301_80739235；E2183-draft-2301_80739235

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 142 | `TBB_TEST=ON`，按 OHOS 目标生成的完整 oneTBB CTest 清单 |
| 集成测试 | 0 | 上游未单独登记集成测试 |
| 其他测试 | 0 | 无其他独立测试入口 |
| **合计** | **142** | 源码清单证据：reports/upstream-inventory.txt；OHOS 支持清单为 136，六项能力排除均按名称记录 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 136 | -6（OHOS 能力差异） | `TBB_TEST=ON`；跳过 resumable 1 项、malloc compliance 1 项和 malloc proxy 4 项；保留其余上游 CTest |
| 集成测试 | 0 | 不变 | 无独立上游集成测试入口 |
| 鸿蒙特有测试 | 1 | +1 | W3 真机消费者验证 parallel_for，证据绑定 run-02 |
| **合计** | **137** | -5（136 个 OHOS 上游测试 + 1 个鸿蒙特有测试） | `F:\\HarmonyPC\\onetbb-2023.1.0-20260905\\w3\\run-02-result-frozen.json` |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，仅做平台能力兼容：用 `check_symbol_exists(pvalloc, "malloc.h")` 驱动通用宏；OHOS 不注册缺失 resumable API 的测试、依赖地址空间限制的 compliance 测试和依赖 malloc proxy 的 4 项测试

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：待当前 HEAD 平台 CI 回读（OHOS 生成清单 142；支持清单 136）
- 新增测试用例通过率：1/1（100%）

补充验证：Windows host Conan create 与 CMakeDeps consumer 通过，消费者输出 `PASS: oneTBB parallel_for computed 1000 elements`。OHOS W3 run-02 在 `10.62.150.125:8022` 完成签名库与真实消费者验证；run-01 的 Ninja 缺失失败保持不可变。Buildbot #41540 在旧 HEAD `86d839949` 上实际执行 141 项，134 项通过、7 项失败，纠正了旧报告的 139/138 统计。当前候选继续打开 `TBB_TEST=ON` 并在 `build()` 调用 `ctest --output-on-failure`；补丁使用 `check_symbol_exists(pvalloc "malloc.h" ...)` 与通用 `TBB_PVALLOC_PRESENT` 定义，保留 overload 测试本身；另以精确目标能力门控 resumable 1 项、malloc compliance 1 项和 malloc proxy 4 项，并保留已通过的 `test_malloc_used_by_lib` 与 `test_malloc_lib_unload`。消费者使用显式失败返回以保持 Release 校验。当前 HEAD 的 136 项通过率以新平台 CI 日志为准。

---

## 补充说明

- 关联 Issue：#2692
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/onetbb-2023.1.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：E2184 记录版本化共享库物理链接名与 Conan CMakeDeps 元数据的绑定规则。目标库无 Conan 依赖；W0 为空闭包并通过，目标真机消费者通过。OHOS 目标生成清单为 142 项，支持清单为 136 项；六项排除分别绑定缺失的 resumable API、地址空间限制和 malloc proxy 能力。Buildbot #41540 的 141 项旧 HEAD 日志只用于核算与失败定位；当前 HEAD 的 136 项结果由新平台 CI 产生。
