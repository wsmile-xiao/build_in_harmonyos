# DRAFT-ohos-conan-libpython-hijacks-host-interpreter — LD_LIBRARY_PATH 上的 conan 版 libpython 会把宿主解释器「换身份」

> Contributor: 3211 / Status: **DRAFT** / Updated: 2026-09-20 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-conan-libpython-hijacks-host-interpreter`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E036` 平台名解析（`uname` 含空格致平台名错） | 已收录 | OHOS `uname -r` 返回 `HongMeng Kernel 1.11.0`（含空格）→ 平台名解析失败，修法是改 `sysconfig.py` / `distutils/util.py` | E036 是**平台名本身**取不到（外部命令返回值问题）；本条是**解释器身份被换**导致 sysconfigdata 模块名不匹配（LD_LIBRARY_PATH 选错 libpython）。二者都会落到 sysconfig·distutils，但**证据与修法完全不同**：E036 改源码，本条调 LD_LIBRARY_PATH |
| `E512` 宿主预装 vs CI 干净导致的 ModuleNotFoundError | 已收录 | 依赖缺失，修法 `add-deps` | E512 缺的是**第三方包**；本条缺的是**宿主 stdlib 里的 sysconfigdata 模块**——补依赖无从下手，因为根本不是依赖问题，而是解释器用错了 libpython |
| `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` | 草稿 | 子进程覆盖 PYTHONPATH → 用独立 venv | 那条管 **PYTHONPATH**（模块查找路径）；本条管 **LD_LIBRARY_PATH**（动态库查找路径）。同一测试环境里两者都会出现，须分别处理 |

**全库查证**：对 `sysconfigdata`、`解释器身份`、`interpreter identity`、`conan 版 libpython` 四组关键词在 `knowledge/drafts/*.kv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md` 中检索，**命中 0 条**（E036 命中 `_sysconfigdata` 但内容为平台名解析，见上表差异）。`DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable` 属元数据缺失，与此无关。

## Scope（何时用）

| 信号 | 检查命令 |
|---|---|
| 报 `No module named '_sysconfigdata__linux_aarch64-linux-ohos'` | 直接观察报错 |
| 报错指向 `sysconfig` / `distutils` 内部，且措辞与你的配置无关 | 观察 traceback |
| 用**宿主**解释器跑测试，而被测包/测试依赖含 conan `python/*` | 检查 conanfile 的 requirements |
| 测试期需要编译扩展或取 `LDSHARED`/`LIBDIR` | 检查测试用例 |
| `sys.platform` 应为 `ohos` 却显示 `linux` | `python3 -c "import sys; print(sys.platform)"` |

## Symptom（真实表现）

cffi 2.1.1 适配中，用宿主解释器跑测试（因 conan python 依赖自带的 `_ctypes` 解析不到 libffi，见下「关联」）时，测试全线报：

```
ModuleNotFoundError: No module named '_sysconfigdata__linux_aarch64-linux-ohos'
```

**欺骗性**：报错在 `sysconfig` 内部，字面上与「LD_LIBRARY_PATH 设错了」毫无关联。

### 复现与对照

```bash
# 含 conan python lib 时
$ LD_LIBRARY_PATH=<conan_python_pkg>/lib python3 -c \
    "import sys, sysconfig; print(sys.platform); sysconfig.get_config_var('CC')"
linux
ModuleNotFoundError: No module named '_sysconfigdata__linux_aarch64-linux-ohos'

# 剔除后
$ python3 -c "import sys, sysconfig; print(sys.platform); sysconfig.get_config_var('CC')"
ohos
clang
```

## Root Cause

conan 的 `python/3.12.x` 依赖在 `package_info()` 里把自身 `lib` 目录注入 `LD_LIBRARY_PATH`（runenv）。用**宿主** `python3` 跑测试时，动态链接器因此解析到 **conan 版 `libpython3.12.so`**，而非宿主解释器预期的那份。

后果是解释器「换身份」：

- `sys.platform` 由 `ohos` 变为 conan **编译期**的 `linux`
- `sysconfig` 于是去找按 conan 编译平台拼出的模块名 `_sysconfigdata__linux_aarch64-linux-ohos`
- 而宿主 stdlib 里只有自己那份（`_sysconfigdata__ohos_*`）
- → 任何 `sysconfig.get_config_var()` 抛 `ModuleNotFoundError`

**隐蔽性**：若测试代码只 `import` 而不调 `sysconfig`，则**完全无感**；直到某个用例需要 `LDSHARED` / `LIBDIR` / 平台判断时才炸——此时报错位置与被测包毫无关系。

## Recommended Solution

### ① 剔除 conan 版 libpython（针对本体测试）

```python
# conanfile.py：测试 env 处理
env["LD_LIBRARY_PATH"] = os.pathsep.join(
    p for p in env.get("LD_LIBRARY_PATH", "").split(os.pathsep)
    if p and os.path.realpath(p) != os.path.realpath(conan_py_lib))   # 按 realpath 比较，防符号链接绕过
env.pop("_PYTHON_SYSCONFIGDATA_NAME", None)   # 清掉可能残留的干扰变量
```

剔除后扩展仍正常：Python 符号由**已在运行的主解释器**解析（即便扩展的 NEEDED 里有 libpython，动态链接器也会复用已加载的同一 soname）。

### ② 对称需求：embedding 类用例必须补上**宿主** libpython

方向相反但同源——内嵌解释器类用例生成的可执行文件 NEEDED 里有 `libpython3.12.so.1.0`，该 .so 不在 `LD_LIBRARY_PATH` 上时会：

```
exit code 127
Error loading shared library libpython3.12.so.1.0
```

做法是把宿主 `LIBDIR` 作为**单项前置**，而非把 conan 版留下：

```python
host_lib = host_sysconfig.get_config_var("LIBDIR")   # 如 <prefix>/lib
env["LD_LIBRARY_PATH"] = os.pathsep.join(
    [host_lib] + [p for p in env["LD_LIBRARY_PATH"].split(os.pathsep) if p])
```

**顺序**：先剔除 conan 版，再前置宿主版。

### ③ 自检断言（防静默出错）

启动时显式断言平台身份，不满足即报错退出：

```python
python3 -c "import sys, sysconfig; assert sysconfig.get_config_var('CC'); print(sys.platform, 'ok')"
```

宁可不跑，也不要在一半功能失效的解释器上跑出一片虚假结果。

### 回退方案（priority 2）

无法安全剔除时（如被测套件确实需要 conan 版），至少加上述断言并**大声失败**，同时把该环境约束写入 `MANIFEST.yml` / `notes.md`。

## 反面模式（forbid）

| 模式 | 为什么禁止 | 后果 |
|---|---|---|
| 把该 `ModuleNotFoundError` 当成被测库或 Python 自身的 bug | 它是**测试进程 LD_LIBRARY_PATH 选错 libpython** 造成的环境污染 | 误报上游问题，返工并污染知识库；若测试只 import 不调 sysconfig，还会**静默产出错误的通过率** |
| embedding 类用例遇 `exit 127` 就直接跳过 | 方向与本体相反但同源：先剔除 conan 版后**必须补上宿主版** | 同一根因在两侧各制造一批失败，却只记「用例不可用」，掩盖真实修法 |

## 验证记录

| 项 | 值 |
|---|---|
| 案例 | cffi 2.1.1（用宿主解释器跑编译型测试；要求来自 conan python 自带 `_ctypes` 无法解析 libffi） |
| 现象 | 测试期 `sysconfig` 抛 `No module named '_sysconfigdata__linux_aarch64-linux-ohos'` |
| 定位 | `LD_LIBRARY_PATH` 含 conan python lib → `sys.platform` 由 `ohos` 变 `linux` → sysconfigdata 模块名不匹配；剔除后 `sys.platform=ohos`、`CC=clang` 正常 |
| 修法 | 按 realpath 剔除 conan python lib；另为 embedding 用例前置宿主 `LIBDIR` |
| 结果 | 套件恢复正常，最终 **1729 passed / 0 failed**；embedding 用例由 exit 127 转通过 |

## 关联

- `E036` — `uname` 含空格致平台名解析失败（同落 sysconfig，但证据与修法不同）
- `E512` — 宿主预装 vs CI 干净的依赖缺失（补依赖可解；本条补依赖无效）
- `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` — 管 PYTHONPATH；本条管 LD_LIBRARY_PATH（须分别处理）
