# draft-pytest-9.1.1-application-dep-skip

## 症状

`conan create` 的**上游套件已经全绿**，`test_package` 却失败：

```
======== Testing the package: Executing test ========
pytest/9.1.1 (test package): RUN: PYTHONNOUSERSITE=1 /data/service/hnp/bin/python3 ".../test_pytest.py" ...
Traceback (most recent call last):
  File ".../test_package/test_pytest.py", line 32, in <module>
    import pytest
  File ".../p/lib/python3.12/site-packages/pytest/__init__.py", line 8, in <module>
    from _pytest._code import ExceptionInfo
  File ".../p/lib/python3.12/site-packages/_pytest/_code/code.py", line 34, in <module>
    import pluggy
ModuleNotFoundError: No module named 'pluggy'

ERROR: pytest/9.1.1 (test package): Error in test() method, line 31
	self.run(f'{py} "{script}" "{pkg}"', env="conanrun")
```

矛盾之处：**依赖明明装好了**。`conan install` 的输出里有

```
pluggy/1.6.0: Already installed! (3 of 5)
pluggy/1.6.0: pluggy installed: /.../p/plugg88ab82a3a766b/p/lib/python3.12/site-packages/pluggy/
```

包目录在磁盘上、内容完整，消费者环境里却没有它的路径。

## 根因

本包 `package_type = "application"`。Conan 2 对 application 的下游传播规则是
**把 `headers`/`libs` 一律置 False、只保留 `run`**
（`conan/internal/model/requires.py::process_package_type()`：

```python
if pkg_type is PackageType.APP:
    # Change the default requires headers&libs to False for APPS
    set_if_none("_headers", False)
    set_if_none("_libs", False)
    set_if_none("_run", True)
```

而"这个依赖是否需要它的文件"由 `Requirement.files` 判定：

```python
@property
def files(self):  # require needs some files in dependency package
    return self.headers or self.libs or self.run or self.build
```

未显式写 `run=True` 时，`headers`/`libs` 已被置 False、`run` 也为假，于是 `files` 为假。
`graph_binaries._skip_binaries()` 只在该条件成立时把节点列入必需：

```python
for req, t in node.transitive_deps.items():
    if req.files or (req.direct and is_consumer):
        deps_required.add(t.node)
```

结果该节点被判 `BINARY_SKIP`，`conan install` 打印

```
Skipped binaries
    iniconfig/2.3.0, packaging/26.3, pluggy/1.6.0
```

被跳过的节点，其 `runenv_info`/`buildenv_info` **不参与环境聚合** —— 所以消费者的
`conanrun` 环境里没有 pluggy，`import pytest` 在导入链第二层就崩。

### 本机为何"全绿"：user site 兜底掩盖了缺口

开发机 `~/.local/lib/python3.12/site-packages` 里恰好有 `pytest`/`pluggy`/`iniconfig`
（这类测试基础设施包几乎必然被 `pip install` 到 user site）。解释器的搜索顺序在
PYTHONPATH **之后**仍会回落到 user site，于是：

| 环境 | `import pluggy` 的来源 | 结果 |
|---|---|---|
| 本机（uid 有 `~/.local` 读权限） | user site 的同名副本 | 看起来全过 |
| CI（另一 uid，读不到该目录） | 无处可回落 | `ModuleNotFoundError` |

这就是"本机 4164 passed、CI `No module named 'pluggy'`"两台主机结论不同的原因 ——
**不是网络、不是依赖没装好，而是环境传递缺了一环**，而本机的 user site 正好补上了。

### 第二处缺口：依赖包自身用了已移除的 API

修到这一步仍不完整。`packaging/26.3` 的配方用 Conan 1.x 的 `env_info` 导出路径：

```python
def package_info(self):
    self.cpp_info.libs = []
    self.env_info.PYTHONPATH.append(...)   # ← Conan 2 已移除该属性
```

CI 日志里对应的只有一行容易被忽略的警告：

```
WARN: deprecated: Usage of deprecated Conan 1.X features that will be removed in Conan 2.X:
WARN: deprecated:     'env_info' used in: packaging/26.3
```

后果是消费者的 `PYTHONPATH` 里有 pytest / iniconfig / pygments / pluggy，
**唯独没有任何 packaging 条目**（实测 `grep -o 'PYTHONPATH="[^"]*"'` 逐项核对）。
`import pytest` 于是从宿主解释器自带的那份 packaging 解析——在本机与 CI 都可能"侥幸"成立，
但这条路径与被测包无关。

## 修复

**① 四个运行时依赖全部显式 `run=True`**（承重项，不是修饰）：

```python
self.requires("iniconfig/2.3.0", run=True)
self.requires("packaging/26.3", run=True)
self.requires("pluggy/1.6.0", run=True)
self.requires("pygments/2.20.0.1", run=True)
```

本机对照实测（假 application 工具 + 四个真实依赖 + 消费者读自己的 conanrun 环境）：

| 声明方式 | 消费者 PYTHONPATH 中 pluggy / iniconfig 命中 |
|---|---|
| 普通 `requires` | 0 / 0（CI 正是这样失败的） |
| `run=True` | 1 / 1 |

**② `no_skip=True` 不能替代 `run=True`**：实测它让 `Skipped binaries` 列表消失
（看起来修好了），但消费者环境仍然拿不到依赖 —— 只解决"跳过"，不解决"传播"。

**③ 构建上下文同理**。用 `tool_requires("pytest/9.1.1")` 引入时（xkeyboard-config
就是这种用法），`conanbuildenv` 里同样只有带 `run=True` 才有这些条目。

**④ 依赖自身导出不可靠时，由本包代为发布**。修 `packaging/26.3` 本身在本 PR 内不可行
（它已发布，且本仓规则一 PR 只放一个包），而"消费者需要什么"本来就是 pytest 的契约。
故在本包 `package_info()` 中探测并发布每个依赖的 site-packages：

```python
dep_sites = []
for name in ("iniconfig", "packaging", "pluggy", "pygments"):
    folder = self.dependencies[name].package_folder      # 取不到 → output.warning 具名告警
    dep_site = self._find_site_packages(folder)          # 探测布局，不硬编码
    dep_sites.append(dep_site)
for env in (self.buildenv_info, self.runenv_info):
    for dep_site in dep_sites:
        env.append_path("PYTHONPATH", dep_site)
```

布局必须**探测而非假设**：`pygments/2.20.0.1` 装到 `lib/python/site-packages`（无版本号），
其余三个装到 `lib/python3.12/site-packages`。成功时打印
`published N dependency site-packages path(s)`（实测 N=4），可由日志复核。

## 验证

```
pytest/9.1.1: pytest installed: .../p/bin/pytest; published 4 dependency site-packages path(s)
entry point invocation: through the interpreter /data/service/hnp/bin/python3 .../p/bin/pytest
PYTEST_CONSUMER=PASS assertions=41
EXIT=0
```

`test_package` 另加了两道防复发断言（41 项中的新增项）：

- 断言 `PYTHONNOUSERSITE=1` 已在生效环境中设置 —— 若未来有人删掉它，会**显式失败**而
  不是静默恢复"user site 兜底"的假通过；
- 逐个断言四个依赖的 `__file__` **落在各自的 package_folder 之下**，把"环境传递正确"
  与"某个 user site 副本恰好满足了 import"区分开。

负向方向同样被覆盖：把 `package_folder` 移走后 `conan test` 必须失败——这正是
`DRAFT-pytest-9.1.1-negative-test-false-pass` 记录的那条防线。

## 适用范围

任何 `package_type = "application"`（或 build-scripts）且带 Python 运行时依赖、
被 `requires`/`tool_requires` 消费的包，在本仓都会遇到同一条传播规则。判别只需两步：

1. `conan install` 输出里有 `Skipped binaries` 列出你的依赖吗？
2. 消费者环境里 `grep -o 'PYTHONPATH="[^"]*"' conanrunenv*.sh` 有该依赖的路径吗？

两问皆"是/否"相反时，就是这个坑。C/C++ 包若产物只用绝对路径调用、不经
PYTHONPATH/PATH 解析，则不受影响。
