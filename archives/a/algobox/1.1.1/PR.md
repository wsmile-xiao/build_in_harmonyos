【知识库扩展】feat(algobox): 1.1.1 适配 HarmonyOS PC

---

## PR 信息

- **三方库名称**：algobox
- **上游版本**：1.1.1
- **上游仓库地址**：https://www.xm1math.net/algobox/
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展）
- **使用知识库**：openharmony-compile-agent（DRAFT-algobox-ohos-target-qmake-windows-host）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游源码未发现 make check / ctest / 专用测试目录 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | 同上 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 无 |
| 集成测试 | 0 | 不变 | 无 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test.sh` 通过 `--version` / `--help` 做 CLI smoke |
| **合计** | **1** | **+1** | |

---

## 上游测试用例修改说明

- [x] **否**，未修改上游任何测试用例

---

## 补全测试用例说明

- [x] **是**，上游无可直接消费的测试入口，适配后补全了 `test_package` smoke

> - **补全的测试范围**：安装后的 `bin/algobox` 版本输出与 help 输出检查
> - **补全原因**：上游没有可直接复用的自动化测试，且该包需要先验证安装产物可执行
> - **新增测试文件清单**：
>   1. `test_package/conanfile.py` — Installed-package smoke test
>   2. `test_package/test.sh` — `--version` / `--help` 校验

---

## 验证结果

- 编译状态：通过（CI #40723 / OpenHarmonyPCDeveloper-CI-031，`conan-build-test` 通过）
- 上游测试用例通过率：0/0（无）
- 新增测试用例通过率：1/1（CI `test_package` 执行 `test_package/test.sh`，`--version` / `--help` 均通过）

### 补充说明

- 本轮已完成前置适配、依赖检查和知识草稿沉淀。
- 本包已改为 QWidget/TextBrowser 浏览器回退路径，不再直接依赖 `qtwebengine/6.11.1`、`qtwebchannel/6.11.1` 或 `qtcore5compat/6.11.1`。
- Windows 本机因 OHOS-target `qmake6` 不可执行，仅做补丁链、语法和静态检查；完整构建与 `test_package` 结果以 CI #40723 为准。
- 任务分支：`feat/algobox-1.1.1`
