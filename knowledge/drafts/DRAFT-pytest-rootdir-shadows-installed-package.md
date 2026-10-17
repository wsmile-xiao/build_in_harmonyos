# DRAFT — pytest 默认 `importmode=prepend` 把 rootdir 插入 `sys.path[0]`，源码树里**未编译**的包目录会遮蔽已安装包

> 触发事件：zstandard 0.25.0 HarmonyOS PC 适配（PR #12210）。`conan create` 的
> 上游测试步骤 28 个测试文件**全数**在收集期失败（2026-09-23 真机实测）。

## 相关既有条目（同族差异化定位）

全库查重（`knowledge/graph/index.tsv` + `knowledge/graph/E*.kv` + `knowledge/drafts/`）：

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| E 编号检索（`importmode` / `import-mode` / `rootdir` / `sys.path[0]` / `backend_c`） | — | `graph/index.tsv` 与 `E*.kv` **0 命中** | 本条为**真增量** |
| `DRAFT-pypi-wheel-vendor-python-dep-closure`、`DRAFT-VENDP-PUREPY-DEP-CLOSURE` | 草稿 | wheel 装配时需自带纯 Python 依赖闭包 | 同属 Python 打包，但讲「依赖要不要 vendor」；本条讲**测试运行期 `sys.path` 顺序**使源码树遮蔽已安装包，机制不同 |

## 错误特征

```
ModuleNotFoundError: No module named 'zstandard.backend_c'
ERROR tests/test_buffer_util.py
ERROR tests/test_compressor.py
...
!!!!!!!!!!!!!!!!!!! Interrupted: 28 errors during collection !!!!!!!!!!!!!!!!!!!!
```

诡异之处：`pip install` 明明已把包装进目标目录、`PYTHONPATH` 也指过去了 ——
`import zstandard` **能成功**，只是里面的 `backend_c` 扩展导入不到。

## 根因分析

### 要点 1：pytest 会把 rootdir 插到 `sys.path[0]`

pytest 默认 `importmode=prepend`：收集测试时把**测试包的父目录**（rootdir，
通常就是 conan 的 `source_folder`）插入 `sys.path[0]`。而测试通常就在源码树里跑
（`cwd = source_folder`），于是：

- `sys.path` 里源码树的 `zstandard/` **排在**已安装包的 site-packages **之前**；
- 源码树的 `zstandard/` 是「未编译的源码目录」—— 有 `__init__.py`、
  `backend_cffi.py`，**但没有编译出来的 `backend_c*.so`**（`bdist_wheel` 把扩展
  放进了 wheel，不在原地）；
- 结果：`import zstandard` 命中源码树那份，`from .backend_c import *` 随即失败。

即「**源码树遮蔽了已安装包**」，与 `PYTHONPATH` 顺序无关（pytest 的插入在最前面）。

### 要点 2：纯 Python 包不会暴露此问题

纯 Python 包源码树那份也能 import，故症状只在**C 扩展/需编译产物**的包上出现。

## 推荐方案

在 `bdist_wheel` 之后再补一次 **`build_ext --inplace`**（复用已编译目标文件，很快），
让源码树里的包目录也带上扩展 —— 这样无论 pytest 从哪一份导入都能工作：

```bash
setup.py bdist_wheel --system-zstd -d <wheels>   # 出包（也完成编译）
setup.py build_ext --inplace --system-zstd       # 把扩展就位到源码树（供 pytest）
pip install --target=<staging> <wheels>/*.whl    # 装包
```

备选：`pytest --import-mode=importlib`（不往 `sys.path` 插 rootdir），但可能与
依赖 `prepend` 语义的上游测试不兼容 —— **优先用 inplace 方案**。

## 禁止做法

- ❌ **不要**只调 `PYTHONPATH` 顺序来「解决」：pytest 的 rootdir 插入在 `sys.path[0]`，
  永远排在你前面。
- ❌ **不要**把「`import <pkg>` 成功」当作包已就绪 —— 顶层 `__init__.py` 能 import
  不代表其编译扩展能被 import。
- ❌ **不要**改用 `--import-mode=importlib` 了事：它改变上游测试的导入语义，可能
  让依赖相对导入/包布局的用例静默改变行为。

## 验证证据

- **主证据**：zstandard 0.25.0（PR #12210）真机实测。
  - 只做 `bdist_wheel` + `pip install --target` → 28 个文件收集期全挂，
    报 `No module named 'zstandard.backend_c'`。
  - 补 `build_ext --inplace` 后 → 232 passed / 1 failed / 59 skipped，
    消费者测试输出 `OK: zstandard 0.25.0 real API ok (... linked zstd (1, 5, 7))`。
- **交叉佐证**：同批 construct/pyxdg/pyenchant（纯 Python）**未**出现该症状 ——
  与「要点 2」一致。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / conan 2.29.1。

## 查重结论

- 对 `import-mode` / `importmode` / `backend_c` 检索：**0 命中**。
- 对「pytest 遮蔽已安装包」检索：无同机制条目；本仓既有条目多为构建期/链接期
  的 `LD_LIBRARY_PATH`/RUNPATH 类处置，与本条「pytest 自身导入模式导致源码树遮蔽」
  的路径不同。
- **盲区声明**：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人
  提交过同主题草稿。
