# objgraph 3.6.2 适配笔记

## 编译环境
- 构建系统: custom（纯 Python 单模块，无编译步骤）
- 编译日期: 2026-09-19
- 编译器: 无（纯 Python，无 C 扩展）
- 状态: built

## 编译步骤

objgraph 是**纯 Python 单模块**（整个库就是顶层 `objgraph.py`，约 1,231 行），
没有 C 扩展、没有编译产物，因此配方没有真正的"编译"阶段：

```bash
# 1) 取源码 + 校验 sha256（conandata.yml，PyPI 官方 URL）
# 2) build()：在源码根真实运行上游测试
python3 tests.py
# 3) package()：仅把 objgraph.py 拷入 lib/python3.12/site-packages
# 4) package_info()：runenv_info/buildenv_info 声明 PYTHONPATH
```

配方用 `package_type = "python-require"`（无二进制产物、不产生 bindirs →
无需 commands.json，R38 不适用），与仓内 `aiohappyeyeballs` /
`test-refcount` 等纯 Python 包先例一致。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 6 个 doctest 失败：`FileNotFoundError: [Errno 2] No such file or directory: 'dot'` | 上游 doctest 会经 graphviz 的 `dot` 渲染 PNG；环境无 graphviz。上游 `appveyor.yml` 明确把 graphviz 作为测试前置（`choco install graphviz` + `dot -V`） | 声明 `test_requires("graphviz/13.1.2")`（ohpcd 已发布，R36 前置核查通过），**不** skip 相关用例 |
| 2 | **加了 `dot` 到 PATH 后 6 个失败依旧**，仍报 `FileNotFoundError: 'dot'` | **OHOS 平台缺陷**：平台 CPython 因 `_IS_HARMONYOS` 强制 `subprocess` 走 `posix_spawn` 快速路径，而 `posix_spawn` **不做 PATH 解析**；objgraph `_present_graph()` 以**裸名** `['dot', '-Tpng', ...]` 启动子进程 | `build()` 注入 `sitecustomize.py` 设 `subprocess._USE_POSIX_SPAWN = False`，改走 fork/exec（`execvpe` 解析 PATH）。与 `archives/m/meson/1.11.0.1` 同一修法，**不改动任何上游测试文件** |
| 3 | `dot -Tpng` 报 `Format: "png" not recognized` | 只把 graphviz 自身 `lib/` 加入 `LD_LIBRARY_PATH` 不够——PNG 渲染要经 gd/poppler/pango/expat 等**整条传递依赖链**的库 | `_dot_env()` 遍历 `self.dependencies` 收集全部 lib 目录，一并注入 `LD_LIBRARY_PATH`；同时设 `GVBINDIR` 指向 graphviz 的插件目录 |
| 4 | 设备 pytest 5.4.3 无法收集（`--import-mode=importlib` 不支持） | objgraph 上游测试**不用 pytest**——入口是自带的 `tests.py`（`unittest.main(defaultTest='test_suite')`） | 直接用 `python3 tests.py` 运行，不引入 pytest |
| 5 | CI 上 `doctest_setup_py_works` 失败：`import setup` → `setup.py:9: from setuptools import setup` → `ModuleNotFoundError: No module named 'setuptools'`（59 项里 1 项失败 → 退出码非 0 → conan create 红） | 上游 `tests.py` 内嵌 doctest 会 `import setup`，触发本包 `setup.py` 顶端对 setuptools 的导入；**CI worker 的 HNP python 不带 setuptools**，而本机/部分 worker 的解释器恰好装了它 → 同一 SHA 时红时绿（#52272 通过、#52317/#52318 失败） | `build()` 内 `_ensure_setuptools()`：先 `import setuptools` 探测，缺失才 `pip install --no-deps --target <build>/_pybootstrap setuptools wheel`（清华源）并把该目录**前置到 PYTHONPATH**；装完复检，仍不可导入则明确报错。**只装进 build 目录，不碰系统 python**（pillow/10.4.0、numpy/2.5.2 的 `_pybootstrap` 同款） |

## 源码修改

**无补丁**。本适配未修改任何上游文件：

- 平台缺陷（`posix_spawn` 不解析 PATH）通过 `build()` 注入的 `sitecustomize.py`
  在运行期修正，上游 `objgraph.py` / `tests.py` 保持原样；
- 图形渲染所需的外部程序由 `test_requires` 正常提供。

## 依赖版本

| 依赖 | 版本 | 性质 | 来源 |
|------|------|------|------|
| graphviz | 13.1.2 | **test_requires**（渲染 doctest 图形） | ohpcd（已发布） |
| python3 | 3.12.9（宿主解释器） | 运行/测试解释器 | 设备自带 |

objgraph 本体**零运行时依赖**——不 import 任何三方包；graphviz 仅在渲染
图像时以子进程调用，属可选能力（缺失时退化为只写 `.dot` 文件）。

## 验证结果

```bash
# 上游测试（R51，build() 内真实运行）
python3 tests.py
# → Ran 59 tests in 4.414s
#   OK (skipped=2)
```

- 上游测试：**59 项，0 failures，2 skipped**
  - 2 个 skip 全为上游自身的 Python 2 专用闸
    （`@skipIf(sys.version_info[0] > 2, "Python 3 has no unbound methods")`，
    见 `tests.py` 的 `test_short_repr_unbound_method` 与
    `test_edge_label_unbound_method`），在任何 Python 3 上都不可达——
    **非依赖缺失、非适配缺陷、非本适配可消除**。
  - 其余 57 项真实执行并通过，其中 **6 个 doctest 实际调用 `dot` 渲染 PNG**。
- test_package 消费者测试（R34 真实 API）：见 `test_package/test_objgraph.py`，
  覆盖导入/版本/导出面/`by_type`/`count`/`typestats`/`safe_repr`/`at_addrs`/
  `get_leaking_objects`/`object_graph`/`shortest_path`/`find_ref_chain`/
  `show_refs`/`show_backrefs`/`show_chain`/`growth`。

## 注意事项

- **`posix_spawn` 不解析 PATH 是通用平台陷阱**，不止影响 objgraph：任何在 OHOS
  上以**裸名**启动外部程序的 Python 代码都会命中（meson 配方的 285 个测试
  失败同源）。判定方法：`subprocess.run(['<裸名>'], ...)` 在程序确实位于
  PATH 且可执行时仍抛 `FileNotFoundError`。
- 修复必须走 `sitecustomize`（`PYTHONPATH` 注入），因为该设置要在**被测进程
  启动时**生效；在配方进程内直接设 `subprocess._USE_POSIX_SPAWN` 不影响
  子进程。
- graphviz 的 `dot` 渲染 PNG 需要整条依赖链的 lib，**仅加 graphviz 自身 lib
  会以 "Format: png not recognized" 报错**（插件加载失败），这个现象容易
  被误判成"graphviz 不支持 png"。
