- **三方库名称**：theft
- **上游版本**：0.4.5（适配后版本：0.4.5.1）
- **上游仓库地址**：https://codeload.github.com/silentbicycle/theft/tar.gz/refs/tags/v0.4.5
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游测试套件未按单元测试分类 |
| 集成测试 | 385 | 来源：`test/test_theft_integration.c`，共 385 个 runtime test invocations |
| 其他测试 | 0 | 无 |
| **合计** | **385** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 384 | -1 | 384/384 通过；`forking_privilege_drop_cpu_limit__slow` 因 OHOS 平台行为限制跳过 |
| 鸿蒙特有测试 | 0 | 不变 | 未新增鸿蒙特有测试 |
| **合计** | **384** | -1 | 上游测试实际执行 384 个，全部通过；另有 1 个平台限制测试跳过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. **修改的测试文件**：`test/test_theft_integration.c`
   - **修改原因**：OHOS 不提供该测试依赖的 `RLIMIT_CPU` 到时信号行为。
   - **修改内容**：在测试注册点增加 `#ifndef __OHOS__` / `#endif`，仅在 OHOS 下跳过 `forking_privilege_drop_cpu_limit__slow`，其余上游测试保持不变。
   - **验证依据**：在 OHOS PC aarch64、clang 15 环境执行等价 CPU 限制探针，使用 `setrlimit(RLIMIT_CPU, 1)` 后以 `timeout -k 2 5` 保护，进程由外部 timeout 以返回码 137 结束，未产生该测试所需的 CPU-limit 信号。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

本次 `test_package` 中的消费者测试属于 Conan 包消费验证，不是因上游缺少测试而补全的测试。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：384/384（100%）；另有 1 个因 OHOS `RLIMIT_CPU` 行为限制跳过
- 新增测试用例通过率：1/1（100%，Conan 消费者测试调用 `theft_hash_onepass`）

## 补充说明

- 本次适配将 Conan 版本从 `theft/0.4.5` 升级为 `theft/0.4.5.1`，用于修复 OHOS Conan profile 中 `os.version` 设置导致的消费解析问题；主 recipe 和 `test_package` recipe 均通过 `configure()` 移除未使用的 `os.version`。
- Conan `requires` 和 `tool_requires` 均为空；系统链接依赖为 `libm`，通过 `cpp_info.system_libs = ["m"]` 声明。
- 适配补丁：`patches/0001-skip-rlimit-cpu-test-on-ohos.patch`。
- Conan 消费者测试结果：1/1 通过；W3 本地 CI 验证通过；W4 独立审计通过，P0/P1 问题为 0。
