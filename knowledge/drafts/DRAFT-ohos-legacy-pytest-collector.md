# DRAFT-ohos-legacy-pytest-collector — 旧式 pytest 收集钩子驱动的用例语料：把 conftest 隔离到子目录

> Contributor: 9BC5 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-legacy-pytest-collector`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-ohos-pytest-host-py312-incompat`（同批）| 草稿 | 宿主 pytest **自身**（插件自动加载 + 断言重写）与 py3.12 不兼容 → 任何套件都跑不起来 | 那条是"**运行器**坏"，修法统一（禁插件自动加载 + `--assert=plain`），对全部测试一视同仁；本条是"**某个收集器**依赖已被重构的旧 API"，修法是**路径隔离**——两组测试分开跑。两者叠加时先修前者 |
| `E410` adapt 上游测试展开 | 已收录 | pytest **默认发现规则**漏掉非标准命名的测试文件 | E410 是"文件命名不合默认模式 → 没被发现"；本条是"**有专门的收集器**接管，但该收集器本身在新环境失效"。修法不同：E410 显式展开文件，本条拆分子目录 |
| `DRAFT-multipledispatch-upstream-consumer-test-boundary` | 草稿 | sdist 裁剪测试 → 分母隔离 | 同为"测试分母要分清"，但触发因不同：那条是**发布产物裁剪**，本条是**收集器兼容性** |

**全库查证**：对 `pytest_collect_file` / `旧式收集器` / `collect_file` / `自定义收集器` /
`用例语料` / `子目录隔离` 等关键词，在 `knowledge/index.tsv`、`knowledge/graph/index.tsv`、
`knowledge/graph/*.kv`、`knowledge/doc/*.md`、`knowledge/drafts/*.kv`、`knowledge/drafts/*.md`
中 grep，**命中 0 条**。

## Scope（何时用）

上游测试不写成多个 `test_*` 函数，而是**数据驱动**：
用例放在数据文件里，由根目录 `conftest.py` 的旧式钩子动态转成测试项。

```python
# conftest.py（docopt 0.6.2 的真实形态）
def pytest_collect_file(path, parent):
    if path.ext == ".docopt" and path.basename.startswith("test"):
        return DocoptTestFile(path, parent)

class DocoptTestItem(pytest.Item):
    def runtest(self):
        result = docopt.docopt(self.doc, argv=self.argv)
        if self.expect != result:
            raise DocoptTestException(self, result)
```

本批实例：**docopt 0.6.2**（`tests/cases/testcases.docopt` + `conftest.py`，164 条用例）。

## Symptom

新解释器 + 新 pytest 下，收集阶段直接报错：

```console
$ python3 -m pytest tests
ImportError while loading conftest '.../tests/conftest.py'.
TypeError: required field "lineno" missing from alias
# 或（不同 pytest 版本）
PytestDeprecationWarning: direct construction of DocoptTestItem has been deprecated,
please use DocoptTestItem.from_parent
```

**危害被放大**：该 conftest 与同目录的常规测试文件（`tests/test_docopt.py`）
**共享收集上下文**——conftest 在 import 期失败，会让同目录的常规测试文件
**一并无法收集**（collected 0）。于是"语料组跑不了"被误判成"整套上游测试跑不了"，
可能进而错误地降低申报口径或误报 FAIL。

> 实测发现：把语料文件与 conftest 隔离后，`tests/test_docopt.py` 立刻可独立收集并
> **39 passed**——证明问题只在收集器，不在测试本身。

## Root Cause

`pytest_collect_file` / `pytest.Item` 这套 API 属于 pytest 的**旧式收集接口**：

1. 其实现直接构造 `pytest.Item` / `pytest.File` 子类（新版本要求 `from_parent` 工厂）；
2. 依赖 `fspath` / `py.path` 等新旧混用接口；
3. 插件化重构后这些路径在**新解释器 + 新 pytest** 组合下会抛
   `TypeError: required field "lineno" missing from alias` 等错误。

关键在于**收集范围**：conftest.py 的生效范围是**其所在目录及其子目录**，
所以把它与常规测试文件放在同一层，等于让一个可能失败的收集器
**劫持了整层目录的收集**。

## Recommended Solution

### 主方案（priority 1）— `path-layout-isolation`

把数据文件与旧式收集 conftest 一起搬进**独立子目录**，常规测试文件留在顶层：

```
tests/
├── test_docopt.py          ← 常规 pytest 文件（稳定可跑）
└── cases/
    ├── conftest.py         ← 旧式收集器，只作用于 cases/
    └── testcases.docopt    ← 用例语料
```

配方 `build()` 内**分组执行、分别回填计数**（R51）：

```python
_run("tests/test_docopt.py")                     # 常规组
if os.path.isfile(os.path.join(tests_dir, "cases", "testcases.docopt")):
    _run("tests/cases/testcases.docopt")         # 语料组，best-effort
```

这样：常规组**始终**可跑（不受收集器影响）；语料组作为附加项，
收集成功则加分、失败也不连坐主组。两组计数在 MANIFEST 中分别申报。

### 回退方案（priority 2）— `install-pinned-pytest`

若必须让旧式收集器在新解释器上运行，可为该组单独安装受控大版本的 pytest
（旧式 `pytest_collect_file` 在新版已重构），仍须隔离插件自动加载：

```bash
python3 -m pip install --target <build>/pytest-pin 'pytest<6'
```

### 禁止做法

- ❌ 删除 `conftest.py` 让测试"通过"——语料组会**静默消失**（分母变小却看似全绿），属以掩盖换通过，违反 R51。
- ❌ 把该 conftest 留在 `tests/` 顶层、同时依赖同目录常规测试文件能收集——局部问题会被放大成"整套不可收集"。

## 单库实证（2026-09-16）

| 库 | 处理 | 结果 |
|---|---|---|
| docopt 0.6.2 | 语料 + conftest 放入 `tests/cases/`；`build()` 分组执行 | `tests/test_docopt.py` **39 passed**；`tests/cases/testcases.docopt`（pytest 5.4.3）**164 passed**；合计 **203 passed**，无失败 |

对照组：隔离前，同目录常规测试文件受 conftest import 失败牵连而无法收集。

> 环境说明：语料组在 pytest 5.4.3 下可收集（该版本仍支持旧式钩子）；
> pytest 9.x 已移除该 API。故配方对该组做**存在性判断的 best-effort 执行**，
> 而非硬依赖——这正是"分组隔离"的价值：一组不可用时另一组照常提供证据。

## 测试覆盖边界

本条只解决"旧式收集器导致**收集失败**"。若收集器能运行但**断言语义**在新版本下改变
（例如用例期望值解析方式变化），不属本条。另外，语料组的计数口径依赖所装 pytest 大版本，
申报时须**注明实测所用 pytest 版本**，否则分母不可比。

## 关联条目

- 相似：`DRAFT-ohos-pytest-host-py312-incompat`（pytest 与 py3.12 不兼容）、`E410`（测试发现规则）
- 差异：见上方差异化定位表
