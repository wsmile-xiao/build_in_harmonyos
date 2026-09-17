# DRAFT-ohos-pytest-host-py312-incompat — 宿主 site-packages 的 pytest 与目标解释器不兼容，上游测试无法运行

> Contributor: 5B09 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-pytest-host-py312-incompat`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E410` adapt 纯 Python 库测试展开 | 已收录 | pytest **默认发现规则**漏掉非标准命名的测试文件 → 只跑一个模块覆盖不全 | E410 是"测试没被**发现**"（收集范围问题）；本条是"测试**跑不起来**"（宿主解释器/插件与 py3.12 不兼容，import 阶段即崩）。修法不同：E410 按文件展开，本条禁用插件自动加载 |
| `E2176`（A7F3 草稿）纯 Python 包依赖与源码封闭性 | 草稿 | CI worker 缺第三方模块（scipy/more_itertools）→ test_package 失败 | E2176 是**被测包的外部依赖**缺失（应显式 SKIP 并另跑目标运行时验证）；本条是**测试运行器自身**坏掉，与被测包依赖无关 |
| `DRAFT-ohos-otmpfile-tmpdir-shim` | 草稿 | 库运行时硬编码 `/tmp` | 无关（运行期临时目录 vs 测试运行器环境） |

**全库查证**：对 `PYTEST_DISABLE_PLUGIN_AUTOLOAD` / `typeguard` / `lineno missing from alias` /
`MarkDecorator` / `pytest_collect_file` 五项关键词，在 `knowledge/index.tsv`、
`knowledge/graph/index.tsv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md`、
`knowledge/drafts/*.kv`、`knowledge/drafts/*.md` 中 grep，**命中 0 条**。

## Scope（何时用）

在 `build()` / 测试阶段用**宿主解释器**跑上游 pytest 回填通过率的所有 Python 包适配。
本批五库全部命中：

| 库 | 触发形态 |
|---|---|
| markupsafe 1.1.1 | `import conftest.py` 崩 → `TypeError: required field "lineno" missing from alias` |
| jinja2 2.10.1 | 同上 |
| pathspec 0.6.0 | 同上 |
| docopt 0.6.2 | 同上 |
| requests 2.22.0 | 同上（另叠加 pytest pre-3.0 的 parametrize 写法）|

## Symptom

未做处理时，连**探针命令**都会失败：

```console
$ python3 -m pytest --version
Traceback (most recent call last):
  ...
AssertionError                      # typeguard 插件的 addini("string") 断言炸掉
```

禁用自动加载后再跑测试，仍可能撞断言重写与 py3.12 字节码不兼容：

```console
$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests
ImportError while loading conftest '.../tests/conftest.py'.
TypeError: required field "lineno" missing from alias
```

**最危险的后果不是报错本身**，而是配方里的探针把"环境坏"判成"pytest 不可用"，
于是 `self.output.warning("pytest unavailable, upstream tests skipped")` 静默跳过整段——
日志看起来"正常运行"，实际 **0 个上游测试被执行**，直接违反 R51。

## Root Cause

宿主 `site-packages` 里的 pytest 及其插件集合是按另一套解释器/版本构建的：

1. pytest 的**断言重写**在收集/import `conftest.py` 时就会编译测试模块，其 AST 处理与
   Python 3.12 的字节码/别名结构不兼容 → `TypeError: required field "lineno" missing from alias`；
2. 部分插件（如 `typeguard`）在 `pytest_addoption` 里调用 `addini("string")`，新版 pytest
   已把合法类型收窄为 `(None,"pathlist","args","linelist","bool")` → `AssertionError`。

两者都发生在**收集阶段**，所以表现为"整个套件连 import 都进不去"。
这是宿主环境的构建方式问题，与被测库无关。

## Recommended Solution

### 主方案（priority 1）— `set-env-var`

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests -q --assert=plain -p no:cacheprovider
```

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`：不加载 site-packages 里的任意插件；
- `--assert=plain`：绕开与 py3.12 不兼容的断言重写（断言语义不变——断言失败仍会让运行失败）；
- `-p no:cacheprovider`：不写宿主缓存。

> ⭐ **关键细节：探针命令必须带同一组变量。**
> `_run_upstream_tests()` 里先用 `python3 -m pytest --version` 探测可用性——若探针不带
> `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，探针自己就会因插件而返回非零，于是被判定为
> "pytest unavailable"，正式测试根本不会执行。实测踩过这个坑。

### 回退方案（priority 2）— `install-pinned-pytest`

若被测套件本身要求特定 pytest 版本（例如旧式 `pytest_collect_file` 收集器在 pytest 9.x
已被移除），可在 build 目录内装一个受控版本再运行，仍须隔离插件自动加载：

```bash
python3 -m pip install --target <build>/pytest-pin 'pytest<6'
PYTHONPATH=<build>/pytest-pin:$PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest ...
```

### 禁止做法

- ❌ 用 `skipif` / `xfail` / `"pytest unavailable"` **掩盖**宿主环境问题——宿主坏 ≠ 上游没测试。R51 要求实测回填真实通过率。
- ❌ 在 `build()` 里裸 `pip install pytest` 覆盖宿主 pytest（污染构建环境、同机多包互相干扰、worker 上可能因权限/网络失败）。

## 单库实证（2026-09-16）

| 库 | 处理 | 结果 |
|---|---|---|
| markupsafe 1.1.1 | 探针+测试均带禁用变量 | **32 passed, 11 skipped**（跳过项为上游 `_speedups` 组）|
| jinja2 2.10.1 | 同上 | **533 passed, 2 failed, 1 error, 3 skipped**（3 项环境差异已逐项定性）|
| pathspec 0.6.0 | 同上 | **42 passed, 2 skipped** |
| docopt 0.6.2 | 同上（两组） | **39 passed + 164 passed = 203 passed** |
| requests 2.22.0 | 同上 | **36 passed, 1 skipped**（自足子集）|

修复前：探针失败 → 五库**全部 0 测试执行**。

## 测试覆盖边界

本条只解决"**测试运行器能否跑起来**"，不解决"测试套件自身的其他环境依赖"。
例如 requests 2.22.0 的 `tests/test_requests.py` 需要外部 httpbin 服务，
`tests/test_utils.py` 用 pytest pre-3.0 的 parametrize 写法——那些是**另外的问题层**，
不属本条，且在各自配方的 MANIFEST.yml 中分别申报了排除理由。

## 关联条目

- 相似：`E410`（测试发现范围）、`E2176`（被测包外部依赖缺失）
- 差异：见上方差异化定位表
