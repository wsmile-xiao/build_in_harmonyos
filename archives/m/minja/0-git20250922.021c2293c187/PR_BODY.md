- **三方库名称**：minja
- **上游版本**：0-git20250922.021c2293c187
- **上游仓库地址**：https://github.com/google/minja
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|---|---:|---|
| 单元测试 | 10 | OHOS `conan create` 中实际执行：`tests/test-syntax.cpp` 1 项、`tests/test-chat-template.cpp` 1 项、`tests/test-polyfills.cpp` 8 项；取数命令 `ctest --test-dir <build_folder> --show-only=json-v1`，运行命令 `ctest --output-on-failure -E ToolTest`；10/10 通过。 |
| 集成测试 | 0 | 无独立上游集成测试目标。 |
| 其他测试 | 0 | 完整模型模板矩阵和 `ToolTest` 需要配置/运行时从 Hugging Face 下载可变模型配置与模板；本次未将这些外部数据用例计作通过。 |
| **合计** | **10** | 本表统计的是本次实际执行的上游 C++ 测试。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|---|---:|---|---|
| 单元测试 | 10 | 不变 | 上述上游 C++ 测试，OHOS Harmony device 实跑 10/10。 |
| 集成测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test_minja.cpp` 在 OHOS aarch64 编译运行，验证基础模板渲染与 chat-template generation prompt。 |
| **合计** | **11** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（仅测试注册/依赖接线，未修改上游测试源码）

> `patches/0001-conan-dependencies-and-offline-tests.patch` 将 JSON 与 GoogleTest 接到 Conan 已发布依赖，并只注册无需在线模型文件的上游 C++ suite。完整模型矩阵由 `tests/CMakeLists.txt` 的 `MODEL_IDS` 配合 `scripts/fetch_templates_and_goldens.py` 在配置阶段从 Hugging Face 拉取 `tokenizer_config.json`/模板；部分 polyfill `ToolTest` 还需对应模型模板文件。它是外部可变模型语料，不是随源码固定的测试数据，故本次明确排除，未计为通过。10 个自包含 C++ 用例全部实跑通过。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

## 验证结果

- 编译状态：通过（HarmonyOS aarch64 `conan create` 退出码 0）
- 上游测试用例通过率：10/10（100%）
- 新增测试用例通过率：1/1（100%）

## 补充说明

- 上游版本绑定精确 commit `021c2293c187789ef13d56c6cfd89c9b134fd80f`，配方由该 commit 的官方 codeload 源码归档及 SHA-256 校验构建。
- 包为 C++17 header-only，目标 `minja::minja`，依赖 `nlohmann_json/3.12.0`。
- 使用独立设备缓存 `CONAN_HOME=~/work/psj/ch-minja`；上游 C++ 测试 10/10，消费者用例 1/1，`CREATE_EXIT:0`。
