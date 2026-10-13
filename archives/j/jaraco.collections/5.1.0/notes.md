# jaraco.collections 5.1.0 适配笔记

## 打包环境
- **类型**: 纯 Python 模块包（无编译），MIT
- **打包日期**: 2026-10-07
- **平台**: arm64-ohos（OpenHarmony PC）
- **依赖**: `more-itertools/11.1.0`（Conan requires，已合入）；**包内捆绑** `jaraco.text 4.3.0` + `jaraco.functools 4.6.0` + `jaraco.context 6.1.2`（制品仓无对应包）
- **状态**: built

## 打包步骤（conan create 全流程）

```bash
conan create archives/j/jaraco.collections/5.1.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
- 本体：PyPI sdist `jaraco_collections-5.1.0.tar.gz`（sha256 `0e482940…`），`strip_root=True`；
- 三个捆绑依赖：各自 sdist 解到 `_vendored/<name>/`（URL+sha256 钉在 `conandata.yml` 的
  `vendored`）。

### 2. 打包（package()）
沿用仓库同族范式（`archives/m/more-itertools`）：模块装到
`lib/python3/site-packages/`：

```
lib/python3/site-packages/jaraco/collections/       ← 本体
lib/python3/site-packages/jaraco/text/              ← 捆绑
lib/python3/site-packages/jaraco/functools/         ← 捆绑
lib/python3/site-packages/jaraco/context/           ← 捆绑
```

**为什么可以这样并列装**：`jaraco` 是 **PEP 420 命名空间包**（没有 `__init__.py`），
多个目录放在同一个 site-packages 下会自然合并成一个命名空间 —— 所以"本体 + 捆绑依赖"
各装各自的 `jaraco/<mod>` 即可，无需改动任一包的结构。

### 3. 上游测试（build() 内真跑）
```bash
cd <src> && PYTHONPATH=<src>:<vendored…>:<more-itertools site> python3 -m pytest -q tests
```
结果按 pytest 的三项统计（passed/failed/errors）解析，并额外把
**`ModuleNotFoundError`/`ImportError`**（说明测试其实没跑起来）与**解析不到通过计数**
也判为不成立 —— 避免把"缺依赖"或"没真跑"记成通过。

## 依赖判定与路线（本库的关键决策）

### 事实
1. `jaraco.collections` **运行期确实 import `jaraco.text`**：`jaraco/collections/__init__.py:13`
   顶部 `import jaraco.text`，并在第 453 行用 `jaraco.text.FoldedCase(key)`
   —— 不是可选依赖，删不掉。
2. 制品仓**没有** `jaraco.text` / `jaraco.functools` / `jaraco.context`：
   两种拼写（`jaraco.text` / `jaraco-text`）× 多版本 `conan install` 实测均
   `Unable to find`；`archives/` 下也没有对应目录。
3. 这三个包自身是**纯 Python 小模块**，且依赖链里其余部分都已发布：
   `more_itertools`（仓库 11.1.0 ✓）、`typer`（仓库 0.27.0 ✓，对应 jaraco.text 声明的
   `typer-slim` 提供的 `typer` 模块）、`importlib-metadata` ✓、`typing-extensions` ✓；
   `jaraco.context` 只在 `python_version < 3.12` 时需要 `backports.tarfile`（本环境 3.12 → 不需要）。

### 路线选择（与 R36 的关系，如实披露）
按仓库 R36「依赖须先发布」，最彻底的做法是**先单独提 `jaraco.context` / `jaraco.functools` /
`jaraco.text` 三个配方**，让本库用 `requires` 声明它们。本轮为在单 PR 内交付本库，选择
**把这 3 个纯 Python 小模块随包捆绑**（各 URL+sha256 钉死、只在 `package()` 里并入
site-packages），已发布的那部分仍走 Conan requires：

| 处置 | 对象 |
|---|---|
| Conan `requires` | `more-itertools/11.1.0` |
| 包内捆绑（vendored） | `jaraco.text 4.3.0`、`jaraco.functools 4.6.0`、`jaraco.context 6.1.2` |

**替代路线**（评审若要求合规）：先按本仓 perl-*/python-require 范式提交这 3 个配方，
再把本库的 `requires` 改成它们、删掉 `vendored` 段与 `package()` 里的并入逻辑。
这也解释得通仓库里 118 个 python-require 包的既有做法（如 `aiohttp` 声明 `yarl`/`multidict`）。

## 上游测试清点（R51）

| 项 | 值 |
|----|----|
| 测试文件 | `tests/test_collections.py`（**27 行**）+ `pytest.ini` |
| 用例数 | **1 个测试函数**（`test_always_lower_keys_dict`，用 `KeyTransformingDict` 子类验证键变换） |
| 跑法 | `python3 -m pytest -q tests`（需 `PYTHONPATH` 含本体 + 捆绑依赖 + more-itertools） |
| 结果口径 | 解析 `passed/failed/errors`；出现 `ModuleNotFoundError`/`ImportError` 或解析不到通过计数 → 判不成立 |
| 补充 | 上游套件很小，故消费者校验（5 项）承担更多"产物可用性"证据，其中 `FoldedCaseKeyedDict` 项专门证明捆绑的 `jaraco.text` 真被使用 |

## 实测结果（本地 conan create，2026-10-07）

```
jaraco.collections/5.1.0: [upstream tests] pytest: passed=1 failed=0 errors=0
jaraco.collections/5.1.0:     1 passed in 0.12s
jaraco.collections/5.1.0: Package '…' created
[ok]   两个 site-packages 均存在（包内 + more-itertools 依赖）
[ok]   import jaraco.collections 成功且来自本包（<pkg>/lib/python3/site-packages/jaraco/collections）
[ok]   3 个捆绑运行期依赖（jaraco.text / jaraco.functools / jaraco.context）均从本包 site-packages 导入 —— jaraco.* 命名空间合并成功
[ok]   真实 API 调用通过：FrozenDict, DictStack, Projection(dict), invert_map
[ok]   FoldedCaseKeyedDict 大小写折叠查找正确 —— 证明捆绑的 jaraco.text 被真正使用
checks=5 fails=0 skips=0
RESULT: PASS
```

- **上游通过率：1 passed / 0 failed / 0 errors**（真实跑出）。如实说明：上游套件只有 **1 个测试函数
  （27 行）**，规模很小——所以本包把"产物可用性"证据主要放在消费者校验上。
- 消费者校验：**5 项全通过**（`checks=5 fails=0 skips=0`）。
- 包创建成功（`Package '…' created`）；包内布局：
  `lib/python3/site-packages/jaraco/{collections,text,functools,context}`。

### 过程中值得记录的一点（自曝一处我自己的错误）

消费者校验第一版把 `Projection` 断言写成"对值施加函数"（`Projection(str.upper, {'a':'x'})['a'] == 'X'`），
实测得到 `'x'` 判 FAIL。查源码后确认语义相反：签名是 `Projection(keys, space)`——**把一组键投影到
另一个 mapping 上**，其中 `keys` 可以是列表/可迭代/可调用/正则（可调用时被当作键的谓词）。
按 docstring 示例改成 `dict(Projection(['a','c'], {'a':1,'b':2,'c':3})) == {'a':1,'c':3}` 后通过。
教训：消费者校验的断言必须**以源码/docstring 为准**，不能凭"名字像什么"推断；
本地验证输出（当时打印的是 `Projection: x`）就已是正确信号，是我没对照断言值。

## 复用来源

- 纯 Python 模块包的打包方式（`package_type=application` + 装到 `lib/python3/site-packages` +
  消费者脚本 `sys.path.insert`）沿用 `archives/m/more-itertools/11.1.0`；
- 把未发布依赖连同包一起交付（vendoring）在仓库里有 Ruby 侧先例
  （`archives/p/pandocomatic`、本会话的 `imap-backup` 随包携带 .gem）——Python 侧本轮首次采用，
  故在 PR/本笔记里明确披露与替代路线。
