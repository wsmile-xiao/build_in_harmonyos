- **三方库名称**：activity-aware-firefox
- **上游版本**：0.4.2+git20250816.c6082f37
- **上游仓库地址**：https://gitlab.com/hook/activity-aware-firefox
- **适配路径**：路径 B（贡献创新/知识库扩展）
- **使用知识库**：E318（Desktop-specific wrapper commands need an explicit context provider，草稿）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游未提供单元测试框架或测试目录 |
| 集成测试 | 0 | 上游未提供自动化集成测试 |
| 其他测试 | 0 | 上游源码仅包含运行脚本和桌面入口 |
| **合计** | **0** | 上游通过率记为 `0/0（N/A）`，不写成 100% |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试框架 |
| 集成测试 | 0 | 不变 | 不虚构上游用例 |
| 鸿蒙特有测试 | 14 | 新增 14 | 对实际打包脚本执行 provider、ID 安全、profile 创建/复用和参数转发断言 |
| **合计** | **14** | **+14** | `test_package/test_activity_context.sh` |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

上游没有自动化测试文件，本提交没有删除、跳过或改写上游测试来制造通过结果。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：新增 14 项功能断言，覆盖显式 OpenHarmony context provider、缺失参数与不安全 ID 拒绝、模板/活动 Firefox profile 创建、已有 profile 复用、profile 路径选择及 Firefox 参数转发。
- **补全原因**：上游脚本把 KDE Activities、X11 显示探测、profile 管理和 Firefox 启动耦合在一起，但没有自动化测试。路径 B 改造需要可复用 provider 契约和防回归验证。
- **新增测试文件清单**：
  1. `archives/a/activity-aware-firefox/0.4.2+git20250816.c6082f37/test_package/test_activity_context.sh` — 14 项实际包内脚本功能断言。
  2. `archives/a/activity-aware-firefox/0.4.2+git20250816.c6082f37/test_package/conanfile.py` — 从 Conan 依赖获取实际 package folder 后调用测试脚本。
  3. `archives/a/activity-aware-firefox/0.4.2+git20250816.c6082f37/test_package/MANIFEST.yml` — 上游与新增测试清单。

## 验证结果

- 编译状态：通过（OHOS/arm64 Conan package revision `0519d27386be903d3dcb8ebce0bc7414`）
- 上游测试用例通过率：0/0（N/A，上游无自动化测试）
- 新增测试用例通过率：14/14（100%）

## 补充说明

- PR 标题已按仓库现行规范使用：`feat(activity-aware-firefox): 0.4.2+git20250816.c6082f37 适配可移植桌面活动上下文`
- 补丁保留 KDE 自动探测，同时新增 `--activity-id`、`--activity-name` 及对应环境变量，供 OpenHarmony launcher、系统参数桥或产品 workspace manager 显式注入稳定上下文。
- `--probe-context` 只用于确定性验证 provider 解析；完整测试仍会创建/复用 profile 并调用记录参数的 Firefox 测试替身，不是仅执行 probe 的空壳测试。
- 显示几何和 GUI 通知在无 X11/kdialog 环境下使用非 GUI fallback，不再阻断核心 profile 流程。
- 路径 B 可复用知识沉淀为 `knowledge/graph/draft/E318-draft-1143.kv` 与配套说明文档，适用于其他把桌面专有服务硬编码进 wrapper 的迁移场景。
- 已知边界：未把真实 Firefox GUI 会话计入测试；公开提交后仍以项目 OHOS runner 的 CI 为最终验收。
