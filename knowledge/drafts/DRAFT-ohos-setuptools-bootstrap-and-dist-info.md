# DRAFT — setuptools 自举构建（无需宿主预装）与 dist-info 的**必需性**：Python 3.12 下 Python 包的构建前置

> 触发事件：setuptools 84.0.0 HarmonyOS PC 适配（PR #11266，2026-09-19 真机实测）；
> 关联修复目标：greenlet 3.5.6（PR #10408）被管理员判 rule 4「缺依赖」166/172，
> 其中构建期即报 `No module named 'setuptools'`（greenlet CI #10488 实测）。

## 背景：为什么 3.12 下 setuptools 是**硬依赖**

Python 3.12 已**移除 stdlib 的 `distutils` 回退路径**。而上游 Python 包的 `setup.py`
普遍在顶层 `import setuptools`：

```python
# setup.py 第一行
import setuptools
```

因此任何走 `setup.py` / `pyproject.toml`（`build-backend = "setuptools.build_meta"`）
构建的包，在 OHOS 上**必须先有 setuptools 可用**，否则构建期直接失败——这不是
"可选工具"，是前置条件。上游 `pyproject.toml` 亦声明
`requires = ["setuptools>=43"]`。

## 要点 1：setuptools 自举 —— **构建它自己**不需要宿主预装 setuptools

适配 setuptools 本身时，一个看似矛盾的问题：构建 setuptools 的 `setup.py` 顶层就要
`import setuptools`，那构建它之前是不是得先有个 setuptools？

**答案是不需要**——只要**构建 cwd 位于解包根**，`import setuptools` 会解析到
**源码树自身**的 setuptools 包：

```text
实测（setuptools 84.0.0 解包根执行）：
  setuptools.__file__    → <解包目录>/setuptools/__init__.py
  setuptools.__version__ → 84.0.0
```

**这条事实的实践价值**：它解释了 greenlet CI #10488 报 `No module named
'setuptools'` 的**根因所在** —— 那个配方当时只能"借用宿主路径"（把宿主的
`setuptools` 目录塞进 `PYTHONPATH`），而宿主 / CI worker 并不保证装有 setuptools
（且版本不可控）。**正确做法**是把 setuptools 作为显式构建依赖声明：

```python
# conanfile.py
def build_requirements(self):
    self.tool_requires("setuptools/84.0.0")   # 或 test_requires，视用途
```

psutil 7.2.2（PR #11263）即用此法：`tool_requires("setuptools/84.0.0")`。

## 要点 2：`dist-info` 是**必需**而非装饰 —— 手工 copy 的包树会让 `__version__` 取不到值

Python 包"源码直拷"交付（把可导入的包目录拷进 `site-packages`）时，容易漏掉元数据
目录（`*.dist-info` / `*.egg-info`）。对**多数**包这只是少了个版本号来源；但对
**setuptools 自身**是**功能性必需**：

```python
# setuptools/version.py
import importlib.metadata
__version__ = importlib.metadata.version("setuptools")
```

`importlib.metadata.version("setuptools")` 是**按 dist-info/egg-info 目录名解析**的，
纯手工 copy 的目录树没有该元数据 → `setuptools.__version__` 取不到值
（`PackageNotFoundError`）。**故 setuptools 必须经 `setup.py` 装配元数据后再打包**，
不能手工 copy 包目录了事。

> 与既有条目的关系：`DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable`
> 覆盖的是**一般 Python 包**"`__version__` 不可用（其余 API 正常）"这一**消费症状**；
> 本条讲的是**构建 setuptools 自身时** dist-info 的**功能必需性**（装配元数据是构建
> 步骤，不是可选补全），层级不同。

## 要点 3：self-hosting 的通用形态

任何**本身就是 Python 构建工具**的包（setuptools、pip、wheel、flit、
build、hatchling 等）适配时都应先回答两个问题：

1. **自举**：它的构建入口是否依赖它自己？若是，确认"cwd 在解包根"能否解析到源码树自身；
2. **元数据**：其运行时是否按 dist-info/egg-info 自我解析（版本、入口点、
   `entry_points`）？若是，打包步骤**必须**装配元数据。

## 推荐方案（下游 Python 包的构建前置）

```python
# conanfile.py —— 任何走 setup.py / setuptools.build_meta 的 Python 包
def build_requirements(self):
    self.tool_requires("setuptools/84.0.0")     # 显式声明，勿借用宿主路径

# 打包时保留元数据（源码直拷场景）
#   接受 *.dist-info 或 *.egg-info（二者皆可被 importlib.metadata 解析）
```

## 禁止做法

- ❌ **不要**在配方里借用宿主 / CI worker 的 `setuptools` 路径（把宿主 site-packages
  塞进 `PYTHONPATH`）：宿主有没有、版本是否兼容都不可控 —— 这正是 greenlet CI
  #10488 报 `No module named 'setuptools'` 的成因。
- ❌ **不要**假设"包目录拷全了就行"：对按元数据自我解析的包（setuptools 自身），
  缺 dist-info 是**功能性故障**，不是少个版本号。
- ❌ **不要**把 `dist-info` 当可选装饰而在打包脚本里忽略它。

## 验证证据

- **主证据**：setuptools 84.0.0（PR #11266）真机实测 —— 自举 `__file__` 指向解包目录、
  `__version__ = 84.0.0`；上游套件 `1 failed, 928 passed, 17 skipped, 51 deselected,
  12 xfailed, 3 xpassed`；消费者 17/17（含"作为 PEP 517 构建后端**真实构建**
  wheel+sdist 并生成 METADATA"的断言）。
- **交叉佐证**：greenlet 3.5.6（PR #10408）CI #10488 报 `No module named
  'setuptools'`；psutil 7.2.2（PR #11263）以 `tool_requires("setuptools/84.0.0")`
  构建成功。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / conan 2.29.1。

## 查重结论

- 对 `自举|bootstrap` 检索：命中 8+ 份**其他构建体系**的自举条目（如
  `DRAFT-aspectc-double-bootstrap-libstdcxx-abi-codesign` 的 libstdc++ 双自举、
  `DRAFT-7324-bglibs-djb-two-stage-cross-build` 的两阶段交叉构建）——均为 **C/C++
  工具链**语境，**无一条覆盖 Python 包的 setuptools 自举**。
- 对 `distutils` 检索：命中 **E177**（`distutils.msvccompiler` 在 3.12 被重命名为
  `_msvccompiler`）、**E036**（平台串进路径）、**E434**（autotools copystamp）——
  均非"3.12 移除 distutils 回退 → setuptools 成为硬依赖"这一前置关系。
- 对 `dist-info` / `importlib.metadata` 检索：命中
  `DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable`（一般包的消费症状）
  与 `DRAFT-multipledispatch-version-metadata-reconciliation`（两个元数据来源**互相
  矛盾**）——本条为"构建 setuptools 自身时元数据的功能必需性"，差异化见上文要点 2。
- **E543 / E544** 讲的是 **C 扩展包**的构建链（ABI/加载权限/basetemp/四重适配链），
  不含"自举"与"元数据必需性"这两点。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过
  同主题草稿。
