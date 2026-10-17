- **三方库名称**：libbitarray
- **上游版本**：2.0
- **上游仓库地址**：https://github.com/noporpoise/BitArray
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 15409 | 来源：上游 `dev/bit_array_test.c`，官方 `make test` 输出 `0 / 15409 tests failed` |
| 集成测试 | 2 | 来源：上游 `dev/bitlock_test.c`、`examples/`，覆盖 pthread bitlock 与 C/C++ 示例执行 |
| 其他测试 | 0 | 无 |
| **合计** | **15411** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 15409 | 不变 | 真机独立运行上游 `make test`，`bit_array_test` 全部通过 |
| 集成测试 | 2 | 不变 | `bitlock_test` 与 C/C++ examples 均通过 |
| 鸿蒙特有测试 | 27 | 新增 | Conan `test_package/test.c` 消费者侧 API 断言 |
| **合计** | **15438** | **+27** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

补充：本 PR 额外新增 Conan `test_package/test.c`，用于验证 HarmonyOS Conan 包作为依赖被消费时的头文件、静态库链接与核心 API 行为；该测试不替代上游测试统计。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：15409/15409（100%）
- 新增测试用例通过率：27/27（100%）

## 补充说明

- issue：#1648
- 用户请求版本为 `2`；Conan 不接受单段版本号，且上游/Debian 版本为 `2.0`，因此 recipe 与目录使用 `libbitarray/2.0`。
- 真机单包 Conan 验证通过：`/storage/Users/currentUser/ohos-test-runs/codex-2.0-libbitarray-2.0-2962a2b5b-conan-20260729-170118-10238`。
- 独立上游测试验证通过：`/storage/Users/currentUser/ohos-test-runs/codex-libbitarray-libbitarray-2.0-upstream-make-test-20260731-031308-30337`。
- 上游 `make test` 覆盖 `dev/bit_array_test`、`dev/bitlock_test`、`examples/example_c`、`examples/example_cpp`；未裁剪上游测试。
