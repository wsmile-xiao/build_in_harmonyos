# 【积分赛事】适配 dot2tex 2.12.0 — Graphviz DOT to LaTeX 转换工具

- **三方库名称**：dot2tex
- **上游版本**：v2.12.0
- **上游仓库地址**：https://github.com/sagemath/dot2tex
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 75 | 来源：上游 tests/ 目录（test_dot2tex.py 59 + test_dotparsing.py 16，unittest 套件） |
| 集成测试 | — | 纯 Python 工具，无独立集成测试 |
| 其他测试 | — | — |
| **合计** | **75** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 3 | 精简（需 Python 解释器执行） | L1 smoke test：CLI --version / 模块导入 / 基本 DOT→TikZ 转换 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 0 | 新增 | 纯 Python 工具，无平台依赖 |
| **合计** | **3** | **精简** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：
  - `test_dotparsing.py`：**16/16（100%）** ✅（纯 Python 解析，无外部依赖，本地实际运行）
  - `test_dot2tex.py`：**13/59 通过**；其余 46 个用例依赖外部 graphviz `dot` 命令
    （`create_xdot` 需调用 `dot` 生成 xdot 数据），OHOS 环境未安装 graphviz，
    运行时报 `FileNotFoundError: dot2tex.log` 无法生成——属外部工具缺失，
    非代码缺陷。上游本身在装有 graphviz 的主机上方可完整运行。
- L1 smoke test 通过率：3/3（100%）
- 新增测试用例通过率：不涉及（无新增测试用例）

## 补充说明

### 变更摘要

首次适配 dot2tex 2.12.0 到 HarmonyOS PC 平台。纯 Python 工具，使用 setuptools 构建，无 C 扩展。

> **上游仓库说明**：原作者 `kjellmf/dot2tex` 已于 2015 年停更（最新版本 2.11.3，无 2.12.0 标签）；`sagemath/dot2tex` 组织 fork 继续维护并发布 2.12.0，是 2.12.0 的唯一持有仓库。故本适配源码 URL、homepage、补丁元数据均指向 `sagemath/dot2tex`。

### 适配内容

1. **conanfile.py**: setuptools 构建，无 C 扩展
2. **conandata.yml**: 源码指向 GitHub 官方源（sagemath/dot2tex）
3. **test_package/**: L1 smoke test（CLI 版本 + 模块导入 + 基本转换）
4. **配方质量**:
   - R27 ✅ `pyparsing/3.1.4`（无 channel 格式；不声明 python3：制品仓无该配方，构建用 sys.executable）
   - R32 ✅ `validate()` 中 `settings.os in ("Linux", "OHOS")`
   - R33 ✅ build() 使用 `sys.executable`
   - R34 ✅ 实质性测试
   - R38 ✅ commands.json 已在软件级目录

### 依赖链

- **pyparsing/3.1.4**（运行时依赖，已发布到制品仓）
- 注：不声明 python3 依赖——制品仓无 python3/3.12.9 配方，构建用 Conan 运行时的 `sys.executable`，运行时 python3 由设备/CI 环境提供（同 pyparsing 配方惯例）

### 质量门禁

| 门禁 | 结果 |
|------|------|
| G0-G4 | ✅ 全部 PASS |
| W2 结构完整性 | ✅ PASS |
| R36 依赖发布 | ⏳ PENDING — pyparsing/3.1.4 先发布（PR #3389 合并后 upload），再构建本包；拓扑序已按 R36 处理 |
| W3 编译验证 | ✅ PASS（.ci-result.json 已写入） |
| W4 Pre-PR 审计 | ✅ PASS（.audit-result.json P0/P1 清零） |
