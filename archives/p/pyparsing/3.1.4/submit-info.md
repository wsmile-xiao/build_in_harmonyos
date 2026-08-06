# 【积分赛事】适配 pyparsing 3.1.4 — Python 解析库

- **三方库名称**：pyparsing
- **上游版本**：v3.1.4
- **上游仓库地址**：https://github.com/pyparsing/pyparsing
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1500+ | 来源：上游 tests/ 目录（pytest 套件） |
| 集成测试 | — | 纯 Python 库，无独立集成测试 |
| 其他测试 | — | — |
| **合计** | **1500+** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 5 | 精简（需 Python 解释器执行） | L1 smoke test：模块导入/版本/基本解析/ParseException/DOT 语法 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 0 | 新增 | 纯 Python 库，无平台依赖 |
| **合计** | **5** | **精简** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖

## 验证结果

- 编译状态：通过
- L1 smoke test 通过率：5/5（100%）
- 新增测试用例通过率：不涉及（无新增测试用例）

## 补充说明

### 变更摘要

新增 pyparsing 3.1.4 完整适配 — Python 解析库（纯 Python，无 C 扩展）。

### 适配内容

1. **conanfile.py**: 基于 setuptools 构建系统的 Conan 2.x 配方，通过 `pip install` 安装
2. **conandata.yml**: 源码声明指向官方 GitHub release tag
3. **test_package/**: 包含 L1 smoke test（模块导入、版本查询、基础解析、ParseException 异常处理、DOT 语法兼容验证）
4. **配方质量**:
   - R32 ✅ OHOS 兼容：`validate()` 中使用 `settings.os in ("Linux", "OHOS")`
   - R33 ✅ 无 shell 变量：build() 使用 `sys.executable`
   - R34 ✅ 实质性测试：test.sh 调用 pyparsing 真实 API

### 依赖链

- **无外部 Conan 依赖**：纯 Python 库，构建使用 Conan 运行时的 `sys.executable`，
  运行时 python3 由设备/CI 环境提供（同 cpython-tkinter 惯例）。
- pyparsing 为纯 Python 实现，无其他外部 Python 依赖。
- 注：R27（`@user/channel` 依赖格式）已废弃；制品仓无 python3/3.12.9 配方，
  故不声明该依赖。

### 测试结果

test_package L1 smoke test 全部通过（5/5）：
- ✅ 模块导入
- ✅ 版本查询（3.1.4）
- ✅ 基础 Word 解析
- ✅ ParseException 异常处理
- ✅ DOT 语法兼容（节点 ID、属性键值对）

### 质量门禁

| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | ✅ PASS |
| G1 配方完整性 | ✅ PASS |
| G2 conan create | ✅ PASS |
| G3 系统同名库隔离 | ✅ PASS（纯 Python，无 .so） |
| G4 产物完整性 | ✅ PASS |
| W2 结构完整性 | ✅ PASS |
| R36 依赖发布 | ✅ PASS（无外部依赖，无需发布） |
| W3 编译验证 | ✅ PASS（.ci-result.json 已写入） |
| W4 Pre-PR 审计 | ✅ PASS（.audit-result.json 已生成） |
