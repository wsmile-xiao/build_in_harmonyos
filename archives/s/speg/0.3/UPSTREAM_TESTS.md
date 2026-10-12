# speg 0.3 — 上游测试记录

> 本文件如实记录 speg 0.3 上游测试的**核实结果**（rule 4——不伪造通过率）。

## 核实结论

**上游 v0.3 没有任何测试文件**（下述三路核验一致）：

| 来源 | 结果 |
|------|------|
| PyPI sdist `speg-0.3.zip`（本任务下载解压） | 仅 `PKG-INFO / setup.cfg / setup.py / speg/{__init__,peg}.py / speg.egg-info/*`——无测试文件 |
| git tag `v0.3`（`b989b7167b5ff582b844c00c26b8a7000b2fe835`）树 | 仅 `.gitignore / .travis.yml / LICENSE / README.md / setup.py / speg/`——无测试目录 |
| `git rev-list --objects --all`（整个仓库全部历史+全部分支） | **`test_peg.py` 从未存在**；测试目录 `tests/` 于 v0.3 之后才引入 |

**v0.3 的 CI 测试**（`.travis.yml`，Python 2.7 + 3.4）：
```sh
script: python ./setup.py install && python -c "import speg"
```
即上游对 v0.3 的"测试"仅是 `import speg` 冒烟。

> 注：master 分支后来重写为 v0.4+ API（`ParsingState`/`Node`/`consume` 等），
> 其 `tests/test_parser.py`、`tests/test_position.py` 与 0.3 的 `speg.peg()` API
> 不兼容，不能用于 0.3。任务提示中的 "test_peg.py（python2.7/3.4 跑过）"
> 经 git 历史核验不存在——此处如实纠正。

## 本地实测（本机 python3）

1. **上游 CI 冒烟**：`python3 -c "import speg"` → ✅ 通过
2. **API 功能验证**（解析简单文法）：
   - `speg.peg('42', rule)` 解析整数文法 → 成功（回调返回 True）
   - `speg.peg('123', rule)` 返回 `123`（int）→ 成功
   - `speg.peg('12x', rule)` 抛 `speg.ParseError`（msg/line/col 正确）→ 成功
3. **适配后消费者测试**（R34）：`test_package/test_speg.py` —— 3/3 断言通过 = 100%

| 项目 | 数值 |
|------|------|
| 上游 v0.3 测试文件数 | 0（不存在——如上核实） |
| 上游 CI 冒烟（import speg） | 1/1 = 100% |
| 适配后消费者 API 断言 | 3/3 = 100% |
