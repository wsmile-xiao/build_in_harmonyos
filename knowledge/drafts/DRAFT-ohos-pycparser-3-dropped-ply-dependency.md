# DRAFT-ohos-pycparser-3-dropped-ply-dependency — pycparser 3.0 去掉 PLY，cffi 链适配面收窄

> Contributor: E5B3 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-pycparser-3-dropped-ply-dependency`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| — | — | — | 全库对 `PLY` / `lex.lex` / `yacc.yacc` 命中 **0 条**；`pycparser` 亦命中 **0 条** |

**全库查证**：对 `PLY`、`pycparser`、`lex.lex`、`yacc.yacc`、`lextab`、`yacctab`
等关键词，在 `knowledge/index.tsv`、`knowledge/graph/index.tsv`、
`knowledge/graph/*.kv`、`knowledge/doc/*.md`、`knowledge/drafts/*.kv`、
`knowledge/drafts/*.md` 中 grep —— **命中 0 条**。

## Scope（何时用）

适配 **pycparser**（尤其经 **cffi** 进入构建链时：cffi → cryptography /
brotlicffi 等）。要点是**版本决定依赖集合**：

| 版本 | 运行时依赖 | 包内生成表 |
|---|---|---|
| 2.x 及更早 | **需要 PLY** | 带 `lextab.py` / `yacctab.py` |
| **3.0** | **无**（仅标准库）| **无** |

## Symptom

版本错配时的典型报错（出现在**使用者 import 时**，非构建期）：

```console
ModuleNotFoundError: No module named 'ply'
ImportError: cannot import name 'lex' from 'ply'
```

> 注意：3.0 正确适配时**不应出现**此错误。它只在"旧配方 + 新源码"
> 或"新配方 + 旧源码"这类错配下浮现。

## Root Cause

pycparser 早期用 **PLY**（Python Lex-Yacc）生成词法/语法分析器。**3.0 改为手写实现**。

实测证据（读 3.0 的 sdist 源码）：

| 检查项 | 结果 |
|---|---|
| `c_lexer.py` 的 import | 仅 `dataclasses` / `enum` / `re` / `typing` |
| `c_parser.py` 的 import | 仅 `.ast_transforms` / `.c_lexer` / `dataclasses` / `typing` |
| `ply` / `lex.lex` / `yacc.yacc` 出现次数 | **0** |
| `lextab.py` / `yacctab.py` | **不存在** |
| `pyproject.toml` 的 `dependencies` | **未声明** |

### 工程意义：适配面收窄

```
cffi ──必需──> pycparser ──(2.x)──> PLY      ← 若为 2.x，多一个前置包
                        └──(3.0)──> 仅标准库   ← 3.0：前置消失
```

pycparser 是 **cffi 的必需依赖**，cffi 又支撑 cryptography 等大量包。
**3.0 让"先适配 ply"这条支线整个消失**——直接减少一个包的适配与发布工作量。

## Recommended Solution

### 主方案（priority 1）— 纯 Python 交付 + 构建期守卫

1. 源码直拷 `pycparser/` 进 site-packages，**不加 ply 依赖**、不引入 `build_requires`；
2. 交付文件含 `c_ast.py`（**上游预生成**后随 sdist 发布，故无需在本配方内调用
   `_ast_gen.py`）与 `_c_ast.cfg` / `_ast_gen.py`（后者本身是可导入的工具模块）；
3. **加构建期守卫**，把"上游回退引入 PLY"拦在构建期：

```python
if "import ply" in open(f"{src}/pycparser/c_parser.py").read():
    raise ConanException("pycparser now imports ply — a ply requirement must "
                         "be added (and ply adapted/published) before shipping")
```

> 守卫的价值：否则一旦上游回退，交付物会是一个**消费者一 import 就 ImportError**
> 的包——错误暴露在使用者那一侧，发现晚、定位难。

### 回退方案（priority 2）— 适配并发布 PLY

仅当必须使用**依赖 PLY 的旧版 pycparser**（消费者钉死 2.x）时：先把 `ply`
适配进制品仓再引入依赖。这是一条真实存在、但**正是 3.0 让它可免于执行**的支线。

### 禁止做法

- ❌ 为 3.0 声明/保留 `ply` 依赖——多声明会因 ply 未发布而卡住依赖闸（PF4）；
- ❌ 把 `No module named 'ply'` 归因于上游缺陷，或靠删 `lextab`/`yacctab` 来"修复"
  ——那是版本错配的症状，正确做法是让配方与源码版本匹配。

## 实测证据（2026-09-16，pycparser 3.0 适配）

| 项 | 结果 |
|---|---|
| 源码 `ply` 依赖 | 0 处（3.0 已移除）|
| `lextab` / `yacctab` | 不存在 |
| 构建期守卫 | 通过（确认无 `import ply`）|
| 上游 pytest | **128 passed, 6 skipped**（0 failed；6 skipped 为需外部 `cpp` 的用例，由上游 `cpp_supported()` 决定）|
| 消费者测试 | PASS（解析真实 C 源码 → 遍历 FileAST/FuncDef/Compound/Return/BinaryOp → CGenerator 回生成 → 畸形输入抛 ParseError）|

## 测试覆盖边界

本条处理"**依赖集合随版本变化**"。区分相邻情形：

- 版本区间不满足（依赖还在，只是版本不对）→ `E241` / `E305`；
- 元数据双来源不一致 → `DRAFT-multipledispatch-version-metadata-reconciliation`。

## 关联条目

- 相似：（暂无同族条目）
- 差异：本条要点是依赖集合**减少**，而非版本号调整
