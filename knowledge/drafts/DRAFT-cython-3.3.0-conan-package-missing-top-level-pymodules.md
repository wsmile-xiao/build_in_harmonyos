# draft-cython-3.3.0-conan-package-missing-top-level-pymodules

## 症状

以 Conan 制品的 `site-packages` 为 `PYTHONPATH`，加载包内**子模块**时立刻失败：

```console
$ env PYTHONPATH=<pkg>/lib/python3.12/site-packages \
      <conan python>/bin/python3.12 -c "from Cython.Compiler import Scanning"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File ".../site-packages/Cython/Compiler/Scanning.py", line 12, in <module>
    from .Visitor import VisitorTransform
  File "Cython/Compiler/Visitor.py", line 13, in init Cython.Compiler.Visitor
  File ".../site-packages/Cython/Compiler/Nodes.py", line 6, in <module>
    import cython
ModuleNotFoundError: No module named 'cython'
```

两个容易把人带偏的特征：

1. **报错的模块名与被适配的包名长得不一样**（包是 `Cython`，报错找 `cython`），
   第一反应往往是「依赖没装 / 装错包」，而实际是本包自己的交付内容缺失。
2. **`bin/` 下的 CLI 入口照常工作**——同一份代码经 `bin/cython` 跑得好好的，
   只有 `site-packages` 形态失败。

## 根因

Python 发行物的 import 拓扑是**两部分之和**，在 `setup.py` / `pyproject.toml` 里并列声明：

| 声明 | 形态 | 安装后位置 | cython 3.3.0 的实例 |
|---|---|---|---|
| `packages=[...]` | **目录**形式的包 | `site-packages/<包名>/` | `Cython/` |
| `py_modules=[...]` | 源码树根的**单文件顶层模块** | `site-packages/<mod>.py` | `cython.py`（`setup.py:515`）|

手工编写 `package()` 的 Conan 配方很容只覆盖 `packages` 那一半——目录名显眼，
一行 `shutil.copytree` 就"完事"了——于是 `site-packages` 里只有 `Cython/`，
没有 `cython.py`。

偏偏 Cython 自身有**多处** `Cython/Compiler/*.py` 在做 `import cython`
（`Nodes.py:6`、`Visitor.py` 等），它们要的正是这个顶层模块：

- 作为**模块**被导入时：`from Cython.Shadow import *`（把 `cython.*` 声明变成空操作）
- 作为 `__main__` 时：才是 CLI 入口

于是加载包内任意子系统模块都会抛 `ModuleNotFoundError`。

**为什么 CLI 不受影响**：`bin/` 下的入口脚本自带自定位

```python
cythonpath, _ = os.path.split(os.path.realpath(__file__))
sys.path.insert(0, cythonpath)
```

而 `site-packages` 形态没有这层兜底——这解释了两个入口行为不一致的迷惑现象。

## 判定顺序（配方侧）

1. 读上游 `setup.py` / `pyproject.toml`，**同时**看 `packages=`（或
   `[tool.setuptools.packages]`）与 `py_modules=`（或 `py-modules`）**两个**清单
   ——配方通常只照抄了前一半。
2. 对 `py_modules` 列出的每个模块，从源码树复制 `<mod>.py` 到 `site-packages` 根。
3. 在 `package()` 里补**存在性断言**：源文件缺失即 `raise`，不静默产出残缺包。
4. 用**消费者视角**验收，而不是只看 build 退出码：以制品 `site-packages` 为
   `PYTHONPATH`，实际 import 包内**最深层**的子模块（如
   `Cython.Compiler.Scanning` / `Visitor`）——只 import 顶层包名往往不触发。

## 修法

```python
# package() 内，copytree 包目录之后
src_mod = os.path.join(src, "cython.py")          # 上游 py_modules=["cython"]
if not os.path.isfile(src_mod):
    raise ConanException(
        "upstream top-level cython.py missing from the source tree — "
        "site-packages would be unusable for 'import cython'")
shutil.copy2(src_mod, os.path.join(site, "cython.py"))
```

## 验证证据

| 验证 | 结果 |
|---|---|
| 修复前：`PYTHONPATH=<site> python -c "from Cython.Compiler import Scanning"` | ✗ `ModuleNotFoundError: No module named 'cython'`（栈指向 `Visitor.py:13` → `Nodes.py:6`）|
| 修复后：同一命令 | ✓ `Scanning + cython OK`，`cython.__file__` = `<site>/cython.py` |
| 制品内容对照 | 修复前 `site-packages/` 只有 `Cython/`；修复后 `Cython/` 与 `cython.py` 并存 |
| `conan test`（test_package） | ✓ `packaged Cython works as a compiler (module + extensions + CLI)` |

## 反模式

- ❌ 只用 `shutil.copytree(源码树/<包名>, site-packages/<包名>)` 就算交付完成
  → 交付物缺顶层模块，消费者 import 包内子模块即失败，且错误模块名与包名不同，
  把排查引向「依赖没装」的错误方向。
- ❌ 只以 `conan create` 的 **build 退出码**判定交付正确
  → build 成功会掩盖包内容残缺；必须消费者视角 import 深层子模块或跑
  `test_package` 才能暴露。

## 适用范围

所有上游同时使用 `packages=[...]` 与 `py_modules=[...]` 的 Python 包（尤其是
"包 + 同名/近名顶层模块" 的布局：cython、旧的 numpy/pandas 辅助模块、
带 `conftest`/`sitecustomize` 式顶层单文件的发行物）。凡配方手工实现
`package()` 交付 `site-packages` 者，都应按本条的清单对照法复核一遍。
