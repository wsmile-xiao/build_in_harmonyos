- **三方库名称**：kicad-templates
- **上游版本**：10.0.0
- **上游仓库地址**：https://gitlab.com/kicad/libraries/kicad-templates
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：官方归档无 `tests/`、pytest 或其他单元测试入口 |
| 集成测试 | 0 | 来源：顶层 `CMakeLists.txt` 无 CTest/`add_test` 注册 |
| 其他测试 | 0 | 上游为纯资源项目，无可执行测试目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 19 | +19 | C++17 消费者探针检查安装路径、资源清点、项目元数据、KiCad 文件解析和反例拒绝 |
| 鸿蒙特有测试 | 1 | 新增 | 针对真实 `__OHOS__`、`access()`、`stat()` 和资源路径的测试 |
| **合计** | **20** | **+20** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：新增 20 个具名消费者检查，覆盖 `KICAD10_TEMPLATE_DIR`、19 个官方项目目录、20 个顶层 worksheet、递归资源数量、项目元数据、KiCad 文件格式解析、截断文件和 malformed JSON 拒绝。
- **补全原因**：上游库仅包含项目模板和 worksheet 资源，没有正式测试框架；Conan 包需要消费者侧测试验证资源安装路径和环境变量。
- **新增测试文件清单**：
  1. `archives/k/kicad-templates/10.0.0/test_package/kicad_templates_probe.cpp` — 20 个具名资源与格式检查
  2. `archives/k/kicad-templates/10.0.0/test_package/conanfile.py` — 通过 `self.run()` 执行消费者探针
  3. `archives/k/kicad-templates/10.0.0/test_package/CMakeLists.txt` — 使用 C++17 构建探针
  4. `archives/k/kicad-templates/10.0.0/test_package/MANIFEST.yml` — 记录测试统计和平台状态

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（0%）
- 新增测试用例通过率：20/20（100%）

## 补充说明

使用 OpenHarmony SDK 26.0.0 clang 15.0.4/CMake 完成 x86_64 OHOS 交叉构建，并在 HarmonyOS 6.0 x86_64 VM 中通过 Conan test 执行探针：`SUMMARY named=20 passed=20 failed=0 deferred=0`。标准 aarch64 profile 仍需具备其指定的 `/data/service/hnp` 工具链后单独验证。
