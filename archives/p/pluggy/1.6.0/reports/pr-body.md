- **三方库名称**：pluggy
- **上游版本**：1.6.0
- **上游仓库地址**：https://github.com/pytest-dev/pluggy
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 124 | 来源：上游 pytest `testing/` 目录，按 pytest 实际收集数统计 |
| 集成测试 | 0 | 上游未单独划分集成测试 |
| 其他测试 | 0 | 无跳过、无 xfail |
| **合计** | **124** | **全部执行** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 124 | 不变 | 完整执行上游 `testing/`，124/124 通过 |
| 集成测试 | 1 | +1 | Conan `test_package` 消费者验证流程，内含 7 项 API 检查，不拆分虚增用例数 |
| 鸿蒙特有测试 | 0 | 不变 | 纯 Python 包，无鸿蒙特有逻辑 |
| **合计** | **125** | **+1** | 上游 124 项全部保留并执行 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

Conan `test_package` 是包消费者边界的集成验证，不属于因上游无测试而补全的单元测试；该流程作为 1 个集成测试用例统计，包含模块导入、版本、marker、PluginManager、historic hook、调用顺序和参数校验共 7 项检查。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：124/124（100%）
- 新增测试用例通过率：1/1（100%）

验证命令：

```bash
python3 -m pytest -q testing/
conan create archives/p/pluggy/1.6.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing -nr
```

Conan 构建日志同时确认上游测试 `124 passed`，消费者测试输出 `All 7 tests PASSED`。

## 补充说明

- 源码使用官方 PyPI sdist，SHA256：`7dcc130b76258d33b90f61b658791dede3486c3e6bfb003ee5c9bfb396dd22f3`。
- 无运行时 Conan 依赖，无源码补丁。
- 已完成 `conan-verify`、W3 本地 CI 和 W4 独立审计；W4 无 P0/P1。
- PR 创建器默认预检误将陈旧本地 `main` 与远端主线之间的 42 个历史包计入本 PR；已独立运行 `ohc.preflight <repo> origin/main HEAD`，PF1-PF6 全部通过，因此创建时显式使用 `--no-preflight`，本 PR 提交实际仅包含 `archives/p/pluggy/1.6.0/`。
