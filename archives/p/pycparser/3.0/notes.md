# pycparser 3.0 适配笔记

## 概述

pycparser 是纯 Python 的 C99 解析器，输出 AST，是 **cffi 的必需依赖**
（cffi 用它解析 C 声明），进而支撑 cryptography 等大量包的构建。

- 上游：https://github.com/eliben/pycparser
- 版本：3.0
- 构建系统：无（纯 Python 包，直接拷贝到 site-packages）
- 许可：BSD-3-Clause
- 编译日期：2026-09-16
- 状态：built

## 最关键的发现：3.0 已移除 PLY 依赖

早期 pycparser 依赖 **PLY**（Python Lex-Yacc）构建词法/语法分析器。**3.0 已改为
手写实现**，实测证据（均来自 sdist 源码）：

| 检查项 | 结果 |
|---|---|
| `pycparser/c_lexer.py` 的 import | 仅 `dataclasses` / `enum` / `re` / `typing` |
| `pycparser/c_parser.py` 的 import | 仅 `.ast_transforms` / `.c_lexer` / `dataclasses` / `typing` |
| `ply` / `lex.lex` / `yacc.yacc` 出现次数 | **0** |
| `lextab` / `yacctab` 生成表文件 | **不存在** |
| `pyproject.toml` 的 `dependencies` | **未声明**（无运行时依赖）|

**这大幅降低了本包与整条 cffi 链的适配成本**：无需先适配并发布 `ply`。

配方里为此加了一条**构建期守卫**：若 `c_parser.py` 中出现 `import ply` / `from ply`，
直接 `ConanException` 失败——防止将来换版本时悄悄引入未适配的依赖，
而不是交付一个消费者一 import 就 ImportError 的包。

## 交付形态

纯 Python，拷 `pycparser/` 下 8 个文件（含 `.cfg`）：

```
__init__.py  _ast_gen.py  _c_ast.cfg  ast_transforms.py
c_ast.py  c_generator.py  c_lexer.py  c_parser.py
```

两点说明：

1. `c_ast.py`（32954 B）是**上游预生成**后随 sdist 发布的（由 `_c_ast.cfg` 经
   `_ast_gen.py` 生成），故无需在本配方内调用生成器；`_c_ast.cfg` 与
   `_ast_gen.py` 一并保留（后者本身也是可导入的工具模块）。
2. sdist 里的 `pycparser.egg-info/` **刻意不拷贝**——那是构建元数据，
   只交付 `pycparser/` 包目录。

## 上游测试

`tests/` 随 sdist 提供（7 个测试文件，`tests/__init__.py` 存在，支持包内相对导入）：

| 文件 | test 数 |
|---|---|
| `test_c_ast.py` | 5 |
| `test_c_generator.py` | 42 |
| `test_c_lexer.py` | 21 |
| `test_c_parser.py` | 59 |
| `test_examples.py` | 1 |
| `test_general.py` | 5 |
| `test_util.py` | 0（辅助）|

**注意 `cpp` 依赖**：`test_c_generator` 与 `test_general` 的部分用例用
`use_cpp=True`，需外部 C 预处理器；上游 `tests/test_util.py` 提供
`cpp_supported()` 探测，缺失时由上游自身的 skipif 跳过（非本适配跳过）。

`build()` 内以 `subprocess` 调 pytest 并回填真实通过率（R51），环境处理沿用既有结论：
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` + `--assert=plain`。
本包结构特殊（`pycparser/` 直接在源码根，不在 `src/` 下），故 `PYTHONPATH`
设为源码根目录。

## 消费者测试（test_package）

`test_package/test_pycparser.py`，全部为真实 API 断言（R34）：

| 组 | 断言 |
|---|---|
| 版本与导出 | `__version__ == "3.00"`（**注意**：与发行版 3.0 不一致，上游如此）、`__all__ == ['c_lexer','c_parser','c_ast']`、`pycparser.CParser is c_parser.CParser` |
| 真实解析 | `CParser().parse()` 解析一段含 `typedef` + `static` 函数 + `main` 的 C 源码，返回 `FileAST` |
| AST 结构 | 顶层声明含 `Typedef`、恰好 2 个 `FuncDef`（add/main）；`funcs['add'].decl.storage == ['static']` |
| 节点遍历 | 函数体是 `Compound`，含 1 个 `Return`，其 `expr` 是 `BinaryOp` 且 `op == '+'` |
| 代码回生成 | `CGenerator.visit(ast)` 输出含 `int add(int a, int b)` / `return a + b;` / `int main(void)` |
| 错误路径 | 畸形 C 源码抛 `ParseError`（并断言异常类型确为解析器的，而非缺模块等无关错误）|

## 验证结果

```
conan create archives/p/pycparser/3.0 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
```

| 项 | 实测结果 |
|---|---|
| `conan create` | **exit=0**，Package created |
| 构建期守卫 | 通过（`c_parser.py` 无 `import ply`/`from ply`，确认 3.0 不依赖 PLY）|
| 上游 pytest | **128 passed, 6 skipped, 128 warnings in 0.63s**（**0 failed**）|
| skip 构成 | 6 skipped 为需外部 `cpp` 的用例，由上游 `cpp_supported()` 探测决定跳过 |
| 消费者测试 | `pycparser 3.00 consumer API: PASS`（6 组断言全过）|

## 注意事项

1. **无需适配 `ply`**——3.0 已移除该依赖（配方有构建期守卫防止将来回退）；
2. `__version__` 是 `"3.00"` 而非 `"3.0"`，断言时勿想当然；
3. `cpp` 相关用例由上游 `cpp_supported()` 探测决定跳过，勿在本侧另加 skip；
4. `--assert=plain` 必需（本机 pytest 5.4.3 的断言重写与 py3.12 不兼容）。
