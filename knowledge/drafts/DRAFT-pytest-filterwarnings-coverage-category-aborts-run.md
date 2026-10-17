# DRAFT — 上游 pytest.ini 的 filterwarnings 引用未安装 Warning 类 → pytest **配置期**即中止（无任何 FAILED 行）

> 触发事件：setuptools 84.0.0 HarmonyOS PC 适配（PR #11266）CI #52255 失败，
> **同一份配方本地却通过**（2026-09-20 真机实测）。

## 错误特征

```
setuptools/84.0.0: [upstream-pytest] pytest.PytestConfigWarning: Failed to import
    filter module 'coverage': ignore:Couldn't import C tracer:coverage.exceptions.CoverageWarning
setuptools/84.0.0: ERROR: Package '...' build failed
ConanException: upstream pytest 运行器异常退出（exit=1），且未解析到失败用例
```

注意：**输出里没有任何 `FAILED` 行**，但退出码非 0。这是本条的识别关键。

## 根因分析

### 要点 1：上游 test extra ≠ 实际运行需求（缺 `coverage`）

上游 `pyproject.toml` 把测试期依赖分散在**多个 extra**（`test` / `check` / `cover` /
`enabler` / `type` / `core`），tox 用的是全集：

```ini
[testenv]
extras = test
    check
    cover      # ← coverage 只在这里（经 pytest-cov 带入）
    enabler
    type
    core
```

而 `pytest.ini` 的 `filterwarnings` 列表里却有：

```ini
[pytest]
filterwarnings=
    error                                          # ← 首行：警告即错误
    ...
    ignore:Couldn't import C tracer:coverage.exceptions.CoverageWarning   # 第 91 行
```

`coverage.exceptions.CoverageWarning` 这个**类**只存在于 `coverage` 包里。
若配方只抄了 `test` extra（不装 coverage），pytest 在**配置期**解析这条过滤器时：

```python
# _pytest/config/__init__.py: apply_warning_filters()
try:
    warnings.filterwarnings(*parse_warning_filter(arg, escape=False))
except ImportError as e:                       # coverage.exceptions 导入失败
    warnings.warn(f"Failed to import filter module '{e.name}': {arg}",
                  PytestConfigWarning)         # ← 改为发警告
    continue
```

而 `filterwarnings = error` 把这个 `PytestConfigWarning` **升级为异常** →
**run 在收集阶段之前就中止**。这就是"没有 FAILED 行却 exit=1"的来源。

### 要点 2：同类的第二处 —— 收集期顶层 import（缺 `jaraco.test`）

```
E   ModuleNotFoundError: No module named 'jaraco.test'
ERROR setuptools/tests/test_dist.py
ERROR setuptools/tests/test_find_packages.py
ERROR setuptools/tests/test_find_py_modules.py
!!!!!!!!!!!!!!!!!!! Interrupted: 6 errors during collection !!!!!!!!!!!!!!!!!!!
```

根因是 `setuptools/tests/compat/py39.py` 顶层：

```python
from jaraco.test.cpython import from_test_support, try_import
```

缺它时 3 个测试文件**收集即 ImportError**，整个 session `Interrupted`。

### 要点 3：为什么"本地通过、CI 失败"

本地宿主 CPython 3.12.9 **恰好装了** `coverage 7.8.0` + `pytest_cov` +
`jaraco.test`（实测），配置期与收集期都被**环境偶然满足**；CI worker 是裸环境 →
同一配方两地结果相反。**故"本地绿"不能作为配方依赖清单完备的证据。**

## 推荐方案

先按**实际报错**补齐隐含依赖，而不是关掉上游的严格策略：

| 报错 | 含义 | 补什么 |
|------|------|--------|
| `Failed to import filter module 'X'` | `pytest.ini` 过滤器引用了未安装包的 Warning 类 | X 对应的包（本例 `coverage`） |
| `Interrupted: N errors during collection` | 测试文件顶层 import 了未声明的包 | 逐个补齐（本例 `jaraco.test>=5.5`） |

```python
# conanfile.py — 测试依赖清单
UPSTREAM_TEST_REQUIRES = (
    # ... 上游 test extra ...
    "coverage",          # pytest.ini:91 引用 coverage.exceptions.CoverageWarning
    "jaraco.test>=5.5",  # tests/compat/py39.py 顶层 import
)
```

**验证必须在干净环境做**（不含宿主 site-packages 的 venv，或 `pip --target` 目录）：

```bash
python3 -m venv /tmp/v && /tmp/v/bin/python -m pip install "pytest>=6"
cd <src> && /tmp/v/bin/python -m pytest --collect-only -q
#   修复前 → PytestConfigWarning: Failed to import filter module 'coverage': ...
#   修复后 → 961/1012 tests collected (51 deselected)，0 errors
```

## 禁止做法

- ❌ **不要**用 `--override-ini=filterwarnings=` / `-W ignore` / `-p no:warnings`
  关掉上游的 `error` 策略来"消除"中止：根因是**依赖缺失**而非策略过严，关掉策略会
  把上游有意的"警告即错误"门禁一并废掉，掩盖真实告警。
- ❌ **不要**只在本地宿主环境跑通就判定配方无误——宿主可能恰好装了缺的那个包
  （本例正是如此），CI 会原样复现失败。
- ❌ **不要**把"无 `FAILED` 行 + 非零退出"记作"没有失败"或直接跳过：无 FAILED 行
  恰说明 run 在收集前就中止，属**未跑成的套件**，不是"无失败"。

## 验证证据

- **主证据**：setuptools 84.0.0（PR #11266）真机实测。
  - 隔离 venv（无 coverage）+ 上游 `pytest.ini` → 复现原文报错
    `PytestConfigWarning: Failed to import filter module 'coverage': ignore:Couldn't
    import C tracer:coverage.exceptions.CoverageWarning`，exit=1。
  - 补 `coverage` 后同一命令 → 报错前移，暴露 `jaraco.test` 收集错误
    （`Interrupted: 6 errors during collection`）。
  - 再补 `jaraco.test>=5.5` 后 → `961/1012 tests collected (51 deselected)`，0 errors。
  - 按配方同款调用形态（`PYTHONPATH=<deps>:<src>`、cwd=源码根）逐文件跑完全部
    36 个顶层 + 5 个 config 测试文件：仅 `test_wheel_mode` 失败（已在允许清单内，
    OHOS hmdfs 不保留 POSIX mode 位）。
- **交叉佐证**：本仓 `humanize 4.16.0` / `inflection 0.5.1` / `pydantic 1.10.19`
  等配方均因上游 `filterwarnings=error` 过严而改用 `--override-ini=filterwarnings=`；
  本条给出的是**另一种、更精确**的处置（补齐被引用的包而非废掉策略）——二者的
  区别在于：那些是"上游策略与 pytest 新版本自身冲突"（PytestRemovedIn10Warning），
  本条是"策略引用了配方未装的包"，后者**不该**关策略。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / pytest 9.1.1 / conan 2.29.1。

## 查重结论

- 对 `filterwarnings` 检索：命中 `humanize 4.16.0`、`inflection 0.5.1`、
  `pydantic 1.10.19`、`aiohttp`、`python-dotenv` 等配方，均为**在命令行覆盖
  `--override-ini=filterwarnings=`** 的处置——**无一条**记录"filterwarnings 项引用
  了未安装的 Warning 类 → 配置期中止"这一机制，也未指出"应补包而非关策略"。
- 对 `PytestConfigWarning` / `Failed to import filter module` 检索：**0 命中**。
- 对 `jaraco.test` / `Interrupted.*during collection` 检索：无同主题条目。
- **E543 / E544** 覆盖的是 **C 扩展包**的运行期构建链（ABI / 加载权限 / basetemp /
  四重适配链），不含"配置期过滤器解析失败"这一路径（basetemp 一条本仓已有沉淀，
  与本条不重叠）。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过
  同主题草稿。
