# DRAFT-ohos-posix-spawn-bare-name-and-find-library-soname — OHOS 上两个必须成对处理的 Python 兼容坑

> Contributor: 3211 / Status: **DRAFT** / Updated: 2026-09-20 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-posix-spawn-bare-name-and-find-library-soname`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E405` posix_spawn 不搜 PATH | 已收录（**已有修法，非仅现象**） | OHOS `subprocess` 走 `posix_spawn`，裸名命令 `FileNotFoundError` | E405 已给出**调用方改写类**修法（`rec_auto_fix: true`：改绝对路径 / `shell=True` / 先 `shutil.which()`）。本条的增量是**那些修法覆盖不到的场合**：当发起调用的代码**不归你掌控**时（如 distutils 内部硬编码 `['cc']`、第三方库内部的 `Popen`），改不了调用方，只能用 sitecustomize 在**进程内补丁 `subprocess.Popen.__init__`**，让裸名在 exec 前被解析。另附该坑在 **distutils 编译器解析**上的高频后果（`['cc']` 默认值 → 任何扩展类测试编译期全炸，实测 cffi 209 项 ERROR），以及最易走错的一步——**只造 PATH shim 无效**（失败点在 exec 语义，不在 PATH 内容） |
| `E068` find_library 崩溃（ldconfig 不存在） | 已收录 | 无 `/sbin/ldconfig` → `ctypes.util.find_library` 抛 SubprocessError / 返回 None | E068 的对策是**改 CPython 源码**（patch `Lib/ctypes/util.py`）；本条给出**不改 stdlib** 的进程内回退（包装 `find_library`，按 soname 探测），并量化影响面（cffi 26 项失败） |
| `DRAFT-apertium-ohos-python-bare-name-test-subprocess` | 草稿 | 上游测试内嵌裸名 `Popen(["python3",...])` | 那条针对**测试源码内**的裸名调用（需改上游/加 wrapper）；本条针对**被测工具链**（distutils 的编译器解析、ctypes 的库查找）——不碰上游源码即可修 |
| `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` | 草稿 | 测试子进程覆盖 PYTHONPATH → 需独立 venv | 那条解决"子进程看不到被测包"；本条解决"子进程找不到可执行文件/库"。两者常同时命中（本条注入的 sitecustomize 恰是**通过 PYTHONPATH 传递**的，故必须放在最前） |
| `E024` Unix socket bind 受限 | 已收录 | AF_UNIX bind EPERM | 无关（但同属"平台能力 vs 环境适配"的区分方法） |

**全库查证**：对 `posix_spawn`、`shutil.which`、`find_library`、`ldconfig`、
`sitecustomize`、`RTLD_GLOBAL` 六项关键词在 `knowledge/graph/*.kv`、
`knowledge/doc/*.md`、`knowledge/drafts/*.kv` 中检索，**无同主题组合条目**。

## Scope（何时用）

在 OHOS 上跑**上游测试套件**的 Python 包适配，尤其是含 embedding / 编译型用例者。

识别信号：

| 信号 | 检查命令 |
|---|---|
| 测试顶层就 `import ctypes` | `grep -n "import ctypes" <src>/testing/conftest.py` |
| 套件里出现裸名命令调用 | `grep -rnE "(check_call\|Popen\|run)\(\[?['\"]?(cc\|gcc\|ccache\|git)" <src>/testing` |
| 出现 find_library 相关失败 | `grep -rn "find_library" <src>/testing` |
| distutils/setuptools 参与编译 | `grep -rn "distutils.ccompiler\|new_compiler" <src>/testing` |

## 坑 A：posix_spawn 不搜 PATH

```
$ python3 -c "import shutil; print(shutil.which('git'))"
/data/service/hnp/bin/git                       # PATH 上明明有

$ python3 -c "import subprocess; subprocess.run(['git','--version'])"
FileNotFoundError: [Errno 2] No such file or directory: 'git'   # 仍然失败

$ python3 -c "import subprocess; subprocess.run(['/data/service/hnp/bin/git','--version'])"
git version 2.45.2                              # 绝对路径 OK
```

根因：hnp CPython 的 `subprocess` 走 `os.posix_spawn()`（**不是** posix_spawnp），
exec 阶段不做 PATH 搜索。

### ⚠️ 最易走错的一步：造 PATH shim

直觉是"没有 `cc`，那就把 clang 软链成 `cc` 挂到 PATH 上"。**实测无效**：
shim 挂在 PATH 首位、`shutil.which("cc")` 能解析到，`Popen(["cc", ...])` 依旧
`FileNotFoundError`。因为失败点在 exec 语义，不在 PATH 内容。

### 正确解法：注入 sitecustomize 补丁 Popen

```python
# <shimmod>/sitecustomize.py —— 必须让该目录排在 PYTHONPATH 最前
import os, shutil, subprocess

def _resolve(command):
    if not isinstance(command, (str, bytes, os.PathLike)):
        return None
    command = os.fspath(command)
    if os.path.dirname(command):
        return command if os.path.isfile(command) else None
    return shutil.which(command)

if not getattr(subprocess.Popen.__init__, "_ohos_path_fix", False):
    _orig = subprocess.Popen.__init__

    def _patched(self, args, *a, **kw):
        exe = kw.get("executable")
        if exe is not None:
            r = _resolve(exe)
            if r is not None:
                kw["executable"] = r
        elif isinstance(args, (list, tuple)) and args:
            r = _resolve(args[0])
            if r is not None:
                args = list(args); args[0] = r
        elif isinstance(args, (str, bytes, os.PathLike)):
            r = _resolve(args)
            if r is not None:
                args = r
        _orig(self, args, *a, **kw)

    _patched._ohos_path_fix = True
    subprocess.Popen.__init__ = _patched
```

**为什么必须用 PYTHONPATH 传**：`site.py` 在解释器启动时 import `sitecustomize`；
放进 PYTHONPATH 后，**子进程也继承**（env 传递），于是 distutils 起的编译器进程
同样受益。

### 高频后果：distutils 的编译器解析

distutils/setuptools 的 Unix 编译器默认值是硬编码的裸名：

```python
# setuptools/_distutils/compilers/C/unix.py
'compiler_so':     ["cc"],
'compiler_so_cxx': ["c++"],
```

因此**任何**走 `new_compiler()` 的编译（embedding 测试、扩展构建）都在编译期炸：

```
distutils.compilers.C.errors.CompileError: [Errno 2] No such file or directory: 'cc'
```

实测 cffi 2.1.1：该坑造成 **209 项 ERROR**，补丁后 → 0。

## 坑 B：无 ldconfig → find_library 恒 None

```
$ python3 -c "import ctypes.util as u; print(u.find_library('m'))"
None
$ python3 -c "import ctypes; ctypes.CDLL('libm.so'); print('OK')"
OK                       # 库其实可用！
```

根因（知识 E068）：OHOS 无 `/sbin/ldconfig`、无 gcc，`find_library` 的三个来源
（`_findSoname_ldconfig` / `_findLib_gcc` / `_findLib_ld`）全部落空。

### 正确解法：进程内按 soname 回退，不改 stdlib

```python
if not getattr(_cu.find_library, "_ohos_soname_fix", False):
    _orig_find_library = _cu.find_library

    def _find_library(name):
        res = _orig_find_library(name)
        if res is not None:
            return res
        for cand in (f"lib{name}.so", f"lib{name}.so.6", f"lib{name}.so.2",
                     f"lib{name}.so.1", f"lib{name}.so.0"):
            try:
                ctypes.CDLL(cand)
            except OSError:
                continue
            return cand
        return None

    _find_library._ohos_soname_fix = True
    _cu.find_library = _find_library
```

实测 cffi：**26 项失败 → 通过**（cffi 的 `ffi.dlopen("m")` 正是经
`_load_backend_lib` → `ctypes.util.find_library`）。

> 与 E068 的关系：E068 的对策是 patch CPython 的 `Lib/ctypes/util.py`（改 stdlib）；
> 本方案在**进程内**包装，不动 stdlib——对 conan 配方更合适（无需重编 Python）。

## 坑 C：musl 不导出 Python 符号 → 现场编译的扩展需 -lpython3.12

cffi 的 `verify()` / `recompile()` 会在测试运行期**现场编译**上百个 C 扩展。
musl 不从主可执行文件导出 Python 符号，这些模块必须显式链接 libpython：

```
ImportError: Error relocating .../_CFFI_test_math_sin...so:
             PyImport_ImportModule: symbol not found
```

而宿主解释器 sysconfig 的 `LDSHARED` 不含 `-lpython3.12`，需测试环境补：

```
LDFLAGS="-L$(python3 -c 'import sysconfig;print(sysconfig.get_config_var("LIBDIR"))') -lpython3.12"
```

实测 cffi：**134 项 ImportError → 0**。

### 反向陷阱：LD_LIBRARY_PATH 上不能同时有 conan 版 libpython

与坑 C 相关的一个陷阱（psutil 7.2.2 先例）：若测试用**宿主**解释器，
必须把 conan `python/3.12.x` 依赖的 `lib/` 从 `LD_LIBRARY_PATH` **剔除**——
否则宿主解释器会改用 conan 版 `libpython3.12.so`（编译时平台为 linux），
`sys.platform` 从 `ohos` 翻成 `linux`、sysconfigdata 名随之改变，宿主 stdlib
里没有对应那份，任何 `sysconfig.get_config_var()` 都抛
`ModuleNotFoundError: No module named '_sysconfigdata__linux_aarch64-linux-ohos'`。

但**embedding 类用例又需要**宿主 libpython 在 `LD_LIBRARY_PATH` 上（它运行
内嵌 CPython 的可执行文件，NEEDED 里有 `libpython3.12.so.1.0`），否则
`exit code 127`。二者需分别处理：先剔除 conan 版，再前置宿主版。

## 反面模式（forbid）

| 模式 | 为什么禁止 | 后果 |
|---|---|---|
| 造 `cc`→clang 的 PATH shim 就以为修好了 | 失败点在 exec（posix_spawn 不查 PATH），不在 PATH 内容 | 在 PATH 上反复打转，误判为"环境缺 cc"，不改结果 |
| 见 `find_library` 返回 None 就判定"库不存在/平台不支持 dlopen" | `ctypes.CDLL("libm.so")` 实际可用；只是**查找方式**失败 | 把可修的环境问题当平台限制，用例被无谓 deselect 或错误上报 env_unsupported |

## 验证记录

| 项 | 值 |
|---|---|
| 案例 | cffi 2.1.1（Python CFFI，C 扩展 + libffi） |
| 初测 | 209 ERROR（坑 A）+ 26 failed（坑 B）+ 134 ImportError（坑 C） |
| 修后 | **1729 passed / 119 skipped / 1 deselected / 4 xfailed，0 failed** |
| 消费者测试 | 23/23 |
| 平台限制（与本条无关的残留） | `test_verify_dlopen_flags`：OHOS 不做 RTLD_GLOBAL 全局符号传播，探针实测后 deselect |

## 关联

- `E405` — posix_spawn 不搜 PATH（本条坑 A 的现象来源）
- `E068` — 无 ldconfig 致 find_library 失败（本条坑 B 的现象来源）
- `E024` — AF_UNIX bind 受限（同属"平台能力"判定，用于对照区分）
- `DRAFT-apertium-ohos-python-bare-name-test-subprocess` — 裸名子进程的另一分支
- `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` — 子进程 PYTHONPATH 覆盖
