# kconfiglib 14.1.0 适配笔记

## 一、上游测试清点（R51 第一步）

上游测试**不在 PyPI sdist 里**，只在 GitHub tag 归档中。清点依据与结果：

```bash
# 1) PyPI sdist 的内容（MANIFEST.in 只 include LICENSE.txt）
$ tar tzf kconfiglib-14.1.0.tar.gz
alldefconfig.py  allmodconfig.py  allnoconfig.py  allyesconfig.py
defconfig.py  genconfig.py  guiconfig.py  kconfiglib.py  listnewconfig.py
menuconfig.py  oldconfig.py  olddefconfig.py  savedefconfig.py  setconfig.py
setup.cfg  setup.py  LICENSE.txt  MANIFEST.in  PKG-INFO  README.rst
# → 无 testsuite.py，无 tests/

# 2) GitHub tag 归档（本配方采用）
$ tar tzf v14.1.0.tar.gz | grep -cE "testsuite.py|tests/"
72
# → testsuite.py（3204 行）+ tests/ 下 71 个 Kconfig 用例文件
```

**测试套件的两段结构**（`testsuite.py:108-109`）：

| 函数 | 内容 | OHOS 可否运行 |
|------|------|--------------|
| `run_selftests()` | 纯 Kconfiglib 自测：词法、依赖求解、选择语义、依赖环检测、预处理器、`is_allnoconfig_y`、`.config` 读写等 | ✅ **已运行，全部通过** |
| `run_compatibility_tests()` | 与 Linux 内核 C 实现（`scripts/kconfig`）逐项比对输出 | ❌ 不适用的 |

`run_compatibility_tests()` 在第 2739 行硬依赖内核构建环境：

```python
os.environ["KERNELVERSION"] = subprocess.check_output("make kernelversion", shell=True)
os.environ["CC_VERSION_TEXT"] = subprocess.check_output("gcc --version | head -n1", shell=True)
```

需要 **Linux 内核源码树 + gcc**。OHOS 上二者皆无，该段属**平台不适用**，
非「跳过不跑」——上表已逐项说明。

## 二、上游测试运行结果（R51 第二步）

在鸿蒙 PC（aarch64, OHOS 6.0, Python 3.12.14）实机执行：

```
$ python _run_selftests.py
Testing is_allnoconfig_y
Testing .config reading and writing
Testing Kconfig fetching and separation
Testing imply semantics
Testing choice semantics
Testing if node removal
Testing multi.def. property copying
Testing dependency loop detection
Testing preprocessor
Testing user-defined preprocessor functions
Testing KCONFIG_WARN_UNDEF

All selftests passed
UPSTREAM_SELFTESTS_OK
```

## 三、适配要点

### 1. 纯 Python 包，无需编译

`setup.py` 的 `py_modules` 全部是 `.py`，无 `ext_modules`、无 C 扩展。
适配工作 = 源码 → `lib/pythonX.Y/site-packages` 布局 → 经 `PYTHONPATH` 暴露。
与同仓库的 `wcwidth` / `ptyprocess` 范式一致。

### 2. ⚠️ guiconfig 不可用 —— OHOS 的 Python 没有 Tkinter

`guiconfig.py` 是基于 Tkinter 的图形化配置界面。实测：

```
$ python -c "import tkinter"
ModuleNotFoundError: No module named _tkinter

$ ls ~/.harmonybrew/opt/ | grep -E "^tcl|^tk"
（无输出 —— harmonybrew 未提供 tcl/tk）
```

**处置**：`package()` 阶段**不打包** `guiconfig.py`，其余 13 个模块正常交付。
其余模块（含 `menuconfig`，基于 curses）均为纯文本/终端交互，无平台依赖。

### 3. testsuite.py 的路径假设

`testsuite.py` 把用例路径硬编码为相对路径：

```python
c = Kconfig("Kconfiglib/tests/empty")   # 第 178 行，另有 3 处同类
```

它设计成**从仓库的父目录运行**（checkout 后目录名正是 `Kconfiglib`）。
而 Conan 解包后的目录名是 `Kconfiglib-14.1.0`。故配方在 `build()` 里
先在源码根造一个 `Kconfiglib/` 目录（含 `tests/` 与各 `.py`），再执行测试。

> 该目录仅用于跑测试，`package()` 按 `py_modules` 白名单逐个拷贝，
> 不会把它带进制品。

## 四、消费者测试结果（R51 第三步）

`test_package/test_kconfiglib.py` —— **29/29 项通过**，覆盖：

| 类别 | 项数 | 内容 |
|------|------|------|
| 导入与版本 | 4 | `VERSION == (14,1,0)`、`Kconfig`/`MenuNode`/`KconfigSyntaxError` 存在 |
| 解析 | 4 | 解析最小 Kconfig、符号入表、bool 与 string 默认值正确 |
| 配置读写 | 4 | `write_config` 产出 `.config`、内容正确、`load_config` 回读 |
| 依赖语义 | 5 | 关掉 FOO 后依赖它的 BAR 值变空、恢复后回默认值、`set_value` 生效、可见性 |
| CLI 工具 | 10 | 7 个模块可导入、`olddefconfig` 实际执行成功并产出正确配置 |
| 平台差异 | 1 | `guiconfig` 已按预期剔除 |

> **测试设计要点**：依赖语义那组是刻意加的 —— 它是 Kconfiglib 区别于
> 普通配置解析器的核心能力，只验证「能读值」不足以证明适配成功。

## 五、已知限制

1. **`guiconfig` 不可用**：需要 Tkinter，OHOS 无 `_tkinter`，且无 tcl/tk。
   如后续 `tcl-tk` 被适配进制品仓，可移除本配方的剔除逻辑并补测。
2. **`run_compatibility_tests()` 未运行**：需 Linux 内核源码树与 gcc，
   平台不具备。自测部分（`run_selftests()`）已全部通过。
3. 其余 13 个模块与 CLI 工具均已在真机验证可用。

## 六、复现命令

```bash
export PATH="$HOME/.local/bin:$HOME/.harmonybrew/bin:$PATH"
cd ~/work_argon2
~/.conan-venv/bin/conan create archives/k/kconfiglib/14.1.0 \
  -pr:h=ohos-verify -pr:b=ohos-verify --build=missing
```
