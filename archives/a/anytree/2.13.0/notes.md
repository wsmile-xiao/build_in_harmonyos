# anytree 2.13.0 适配笔记

## 概述

anytree 提供轻量级 Python 树数据结构，含遍历迭代器、搜索、解析器、渲染器与
字典/JSON 导入导出。

- 上游：https://github.com/c0fec0de/anytree
- 版本：2.13.0
- 构建系统：无（纯 Python 包，递归拷贝到 site-packages）
- 许可：Apache-2.0
- 编译日期：2026-09-16
- 状态：built

## 与早前纯 Python 包的两点结构差异

### ① 有子包 → 必须**递归**拷贝

markupsafe / itsdangerous / pycparser 都是**扁平**包（一层 `.py` 文件），
而 anytree 含 **5 个子包**：

```
anytree/
├── __init__.py  cachedsearch.py  config.py  dotexport.py  render.py  resolver.py
│   search.py  walker.py
├── exporter/   (dictexporter.py / dotexporter.py / jsonexporter.py / mermaidexporter.py)
├── importer/   (dictimporter.py / jsonimporter.py)
├── iterators/  (abstractiter.py / levelordergroupiter.py / levelorderiter.py
│                / postorderiter.py / preorderiter.py / zigzaggroupiter.py)
├── node/       (anynode.py / lightnodemixin.py / nodemixin.py / node.py
│                / symlinknode.py / symlinknodemixin.py / util.py / exceptions.py)
└── util/
```

故 `package()` 用 `shutil.copytree(...)`（忽略 `__pycache__`/`.pyc`），
并**逐个断言 5 个子包的 `__init__.py` 存在**——若拷贝方式写成"只拷一层文件"，
子包会静默丢失，而消费者在 `import anytree.exporter` 时才报错。

### ② `__version__` 是**陈旧值**（上游 quirk）

实测对比：

| 来源 | 值 |
|---|---|
| 发行版（tarball 名 / `PKG-INFO`）| **2.13.0** |
| 模块 `src/anytree/__init__.py` | **2.12.1** |

上游 `pyproject.toml` 用 `[tool.pdm.version] source = "scm"`（版本取自 git tag），
而源码树里的 `__version__` 字面量未同步更新。

**消费者测试因此固化真实模块值 `"2.12.1"`**（并把发行版 2.13.0 写进注释），
把不一致**显式记录**下来，而不是想当然断言 2.13.0 然后在 CI 上炸掉。

## 依赖

**无运行时依赖**（`pyproject.toml` 的 `dependencies = []`，实测确认）。

上游 `[build-system]` 用 **pdm-backend**：

```toml
[build-system]
requires = ["pdm-backend"]
build-backend = "pdm.backend"

[tool.pdm.build]
includes = ["src/anytree"]
```

**但本配方不调用 PEP 517 构建**——与仓内其他 Python 包一致，只把可导入的
`src/anytree` 整棵树拷进 `site-packages`。因此**不需要 `build_requires`**，
也避开了 `pdm-backend`（ohpcd 未发布）是否可用的前置问题。

## 上游测试

`tests/` 随 sdist 提供：**26 个 `.py` 测试文件**（总 45 个文件，含
`tests/refdata/` 参照数据），`tests/__init__.py` 存在故支持包内相对导入。

### 一个真阻塞：4 个文件在**收集期** import `test2ref`

```
tests/test_dotexport.py          import test2ref
tests/test_dotexporter.py        import test2ref
tests/test_mermaidexporter.py    import test2ref
tests/test_uniquedotexporter.py  import test2ref
```

`test2ref` 属上游 `[dependency-groups] dev` 组（**非运行时依赖**），
**未发布到 ohpcd**，按 **PF4** 不能作 `test_requires`。由于该 import 发生在
**收集阶段**，**整个套件都会中断**：

```
ERROR tests/test_dotexport.py
!!!!!!! Interrupted: 4 errors during collection !!!!!!!
```

**处置（R51 如实申报）**：配方在 `build()` 内**显式探测这些文件是否存在、
显式 `--ignore` 排除、并输出排除理由**（含"test2ref 是 dev 组工具、未发布"），
而非静默跳过。排除后实测 **143 passed**（其余 22 个文件）。

> 若将来 `test2ref` 发布到 ohpcd，把 4 个 `--ignore` 去掉即可自动纳入。

`build()` 内以 `subprocess` 调 pytest 并回填真实通过率，环境沿用既有结论：
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` + `--assert=plain`（宿主 pytest 5.4.3 的断言
重写与 py3.12 字节码不兼容）。

## 消费者测试（test_package）

`test_package/test_anytree.py`，全部为真实 API 断言（R34）：

| 组 | 断言 |
|---|---|
| 版本与导出 | `__version__ == "2.12.1"`（**上游陈旧值**）、`__all__` 33 项、关键名字在列 |
| 建树 | `is_root` / `parent` / `children` / `height` / `depth` 语义 |
| 路径与后代 | `path` 元组、`descendants`、`leaves` |
| **遍历顺序** | `PreOrderIter` = root,a,a1,a2,b；`LevelOrderIter` = root,a,b,a1,a2；`PostOrderIter` = a1,a2,a,b,root；`ZigZagGroupIter` 分层 |
| 搜索 | `find` / `findall` / `find_by_attr` / `findall_by_attr` |
| Resolver | `resolver.get(root, "a/a1") is a1`、`"/b" is b` |
| AnyNode | 字典式节点（额外属性 `value`）|
| 导入导出往返 | `DictExporter` → `DictImporter` 结构一致 |
| 渲染 | `RenderTree` 输出行数与首行 |
| 错误路径 | 构造环 → `LoopError`/`TreeError` |
| **跨子包导入** | `from anytree.exporter import ...` 等 5 个子包全导入（子包缺失即失败）|

## 验证结果

```
conan create archives/a/anytree/2.13.0 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
```

| 项 | 实测结果 |
|---|---|
| `conan create` | **exit=0**，Package created |
| 上游 pytest | **143 passed, 33 warnings in 0.39s**（**0 failed**）|
| 排除说明 | 4 个 `test2ref` 依赖文件已按 R51 **显式 `--ignore` 并输出理由**（配方日志中可见 excluding 警告），非静默跳过 |
| 消费者测试 | `anytree 2.12.1 consumer API: PASS`（10 组断言全过）|

### 实测订正：Resolver 绝对路径语义

消费者测试初版按**假设**写了 `resolver.get(root, "/b")`，实测报错：

```
anytree.resolver.ResolverError: unknown root node '/b'. root is '/root'.
```

逐项实测绝对/相对路径语义后订正为：

| 写法 | 实测结果 |
|---|---|
| `"a/a1"` | → a1（相对路径，从给定节点向下）|
| `"b"` | → b |
| `"/root/b"` | → b（**绝对路径须以根节点自身名字开头**）|
| `"/b"` | `ResolverError`（未知根节点）|
| `"root/b"` | `ChildResolverError`（被当作子节点名查找）|

修正后断言覆盖三种正确写法 + 两种错误路径。

## 注意事项

1. **必须递归拷贝**（`copytree`）并断言 5 个子包完整——扁平拷贝会静默丢子包；
2. **`__version__` 断言用 2.12.1**（上游陈旧值），不要想当然写 2.13.0；
3. 4 个 test2ref 依赖的测试文件须 `--ignore` 并输出理由（R51），不可静默跳过；
4. `--assert=plain` 必需（本机 pytest 5.4.3 的断言重写与 py3.12 不兼容）。
