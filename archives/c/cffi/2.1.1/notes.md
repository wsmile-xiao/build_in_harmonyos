# cffi 2.1.1 — OHOS（鸿蒙 PC）适配笔记

## 概述

cffi 是 Python 的 C Foreign Function Interface（调用 C 代码的 FFI 库）。本包提供
纯 Python 层 `cffi/` 与加速后端 C 扩展 `_cffi_backend`（链接外部 libffi）。
属**必须编译**的 Python 包（与仓内 psutil / lxml / pillow 同类），
`os=OHOS, arch=armv8`，路径 A 基础适配 + 测试环境适配。

上游版本对应：2.1.1（`github.com/python-cffi/cffi`）。

> ⚠️ **同名不同物**：本仓 `archives/c/cffi/0.24.1` 是**另一个**上游
> （`github.com/cffi/cffi`，Common Lisp 的 FFI 库），与本包无任何关系。
> Conan 引用带版本（`cffi/0.24.1` vs `cffi/2.1.1`），不会互相解析到。

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | setuptools（pyproject `build-backend = setuptools.build_meta`，要求 >=77.0.3） |
| 编译日期 | 2026-09-20 |
| 目标 | aarch64-linux-ohos（`os=OHOS, arch=armv8`） |
| 工具链 | clang 15（OHOS profile），`-fuse-ld=bfd` |
| 状态 | built（本地 `conan create` exit=0） |

## 编译步骤

```bash
conan create archives/c/cffi/2.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

1. `source()` 下载 PyPI sdist（sha256 校验）并解压
2. `build()` 引导 setuptools（pip 镜像）→ `setup.py build_ext --inplace` 编
   `_cffi_backend` → 签名 → 跑上游 pytest 套件（38 个模块）
3. `package()` 拷 `src/cffi` + `_cffi_backend*.so` → 再签一次 → 声明 PYTHONPATH
4. test_package 消费者测试 23 条断言

## 遇到的问题与解决方案

本包共 8 个问题，**全部属测试/构建环境适配，无任何上游源码补丁**
（`patches: {}`）。

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `build_ext` 产物找不到（`build_ext produced no _cffi_backend extension module`） | 上游用 `package_dir={"": "src"}`，distutils 的 `--inplace` 把 .so 拷到 **cwd 下的 src/**，即 `<source_folder>/src/`，而 `basic_layout()` 下 source_folder 即构建根 | 加 `_find_backend_so()` 依次探测 `<source_folder>/src` 与 `<source_folder>`（实测 `copying build/lib.../_cffi_backend...so -> src`） |
| 2 | `import _cffi_backend` 报 `Permission denied` | OHOS 要求被 dlopen 的 .so 带 `.codesign` 段（E212） | build 期与 package 期各签一次（conan 的 `copy()` 会使既有签名失效），用 hnp 的 `binary-sign-tool` |
| 3 | 测试进程 `_ctypes` 加载失败：`ffi_prep_closure_loc: symbol not found` | python 依赖自带的 `_ctypes` 解析不到 libffi；而 `testing/conftest.py:4` 顶层就 `from ctypes import util` → 整个 session 收集期崩溃（exit=4） | 用**宿主**解释器跑 pytest（宿主 ctypes 正常；两者同为 CPython 3.12/aarch64-linux-ohos，ABI 兼容，实测宿主导入扩展成功、`ffi.new` 正常）。psutil 先例同一结论 |
| 4 | cffi1 出现 **134 项** `ImportError: Error relocating ...: PyImport_ImportModule: symbol not found` | cffi 的 `verify()/recompile()` 在测试运行期**现场编译**上百个 C 扩展；musl 不从主可执行文件导出 Python 符号，这些模块必须显式链接 libpython，而宿主 sysconfig 的 `LDSHARED` 不带 `-lpython3.12` | 测试环境补 `LDFLAGS="-L<host lib> -lpython3.12"`（实测补后 134 项 → 0） |
| 5 | **209 项 ERROR**：`CompileError: [Errno 2] No such file or directory: 'cc'` | 上游 `test_ownlib.py:177` 用**裸名** `cc` 调编译器，而 OHOS 只有 clang 没有 cc。**关键**：造 `cc`→clang 的 PATH shim **无效**——OHOS 的 `subprocess` 走 `os.posix_spawn()`（非 posix_spawnp），对裸名不做 PATH 搜索（E405） | 按 pillow 10.4.0 先例注入 `sitecustomize.py`，补丁 `subprocess.Popen.__init__` 用 `shutil.which` 解析裸名后再 exec（实测 209 项 ERROR → 0） |
| 6 | embedding 类 17 项 `exit code 127`：`Error loading shared library libpython3.12.so.1.0` | 见 #3 的"反向需求"：剔除 conan 版 libpython 后，embedding 用例**编译并运行内嵌 CPython 的可执行文件**需要宿主 libpython 在 `LD_LIBRARY_PATH` 上 | 把宿主 `LIBDIR` 前置到 `LD_LIBRARY_PATH`（实测 5 failed → 5 passed） |
| 7 | **24 + 2 项** `OSError: ctypes.util.find_library() did not manage to locate a library called 'm'/'dl'` | OHOS 无 `/sbin/ldconfig` 且无 gcc（知识 **E068**），`find_library` 恒返回 None——但 `libm.so`/`libdl.so` 实际可 dlopen；cffi 的 `ffi.dlopen("m")` 正是经 `_load_backend_lib` 调 `find_library` | 在 sitecustomize 里包装 `ctypes.util.find_library`：原生返回 None 时按 soname 顺序（`lib{n}.so`、`.so.6/.2/.1/.0`）用 `CDLL` 探测（实测 26 项失败 → 通过） |
| 8 | zintegration **7 项** `ModuleNotFoundError: No module named 'distutils'` | 我把构建期 setuptools 引导目录放进测试 `PYTHONPATH`——PYTHONPATH 条目**不执行其 `.pth`**（`distutils-precedence.pth`），于是子进程只有 setuptools 顶层包而无 distutils shim；嵌套 venv 里 `pip install setuptools` 因"already satisfied"跳过，其 distutils 仍未供给 | **从测试 PYTHONPATH 移除 setuptools 引导目录**，让嵌套 venv 各自正常安装（实测 7 项 ERROR → 8 passed） |
| 9 | `test_verify_dlopen_flags` 1 项 `ImportError: ... foo_verify_dlopen_flags_1: symbol not found` | OHOS 加载器**不做 RTLD_GLOBAL 全局符号传播**（纯 ctypes 探针实测复现：liba.so 以 RTLD_GLOBAL 载入后，引用其符号的 libb.so 仍 `symbol not found`）；属平台能力限制 | 加 `_rtld_global_propagates()` **先探针实测**，仅在确认不支持时 `--deselect` 该用例（平台放开即自动恢复，不写死跳过） |

## 源码修改

**无补丁**（`patches: {}`）。上述 9 项全部是**构建/测试环境适配**（`env_prefix`、
`sitecustomize` shim、CC shim、签名、探针），未改动上游任何源文件。

## 依赖版本

| 类型 | 依赖 | 说明 |
|---|---|---|
| 运行/链接 | `python/3.12.9` | Python.h + libpython3.12.so（musl 需显式链接） |
| 运行/链接 | `libffi/3.5.2` | `_cffi_backend` 唯一外部链接依赖；static-library，带 ffi.h/libffi.a/libffi.pc |
| 运行（Python 层） | `pycparser/3.0` | `cffi/cparser.py` 运行期 `import pycparser` |
| 构建期 | setuptools>=77.0.3 | **ohpcd 无制品**，按 PF4 不写 tool_requires，构建期从平台 pip 镜像引导 |
| 测试期 | pytest>=7 | ohpcd 无制品，构建期从平台 pip 镜像取到独立目录 |

## 验证结果

```bash
# 完整门禁
conan create archives/c/cffi/2.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → exit=0

# 上游套件（build() 内运行）
# → 1729 passed, 119 skipped, 1 deselected, 4 xfailed in 916.29s (保留日志 .ci_logs/conan_build_cffi_2.1.1.log)
#   （deselected: testing/cffi1/test_verify1.py::test_verify_dlopen_flags，平台限制）

# 消费者测试
python3 test_package/test_cffi.py <site-packages>
# → 23/23 checks passed
```

**R51 如实申报**：上游 **38 个 test_*.py 模块**（cffi0 16 + cffi1 17 + embedding 5），
实测 **1729 passed / 119 skipped / 1 deselected / 4 xfailed**，**零失败**
（通过率 = 1729/1729 = 100%）。
- 119 skipped：上游自身 `skipif`（win32/bsd 分支、缺可选依赖等）
- 1 deselected：`test_verify_dlopen_flags`，平台限制（RTLD_GLOBAL 不传播）
- 4 xfailed：上游自身标记的预期失败

## 交付物

```
<pkg>/lib/python3.12/site-packages/
├── cffi/                              # 纯 Python 层（含 4 个头文件 package_data）
└── _cffi_backend.cpython-312-aarch64-linux-ohos.so   # C 扩展（已签名）
```

## 注意事项

- **同名不同物**：`cffi/0.24.1`（Common Lisp）与 `cffi/2.1.1`（Python）是两个
  不相关的上游。下游引用务必带版本号。
- **签名不可省**：未签名的 .so 在 OHOS 上 `dlopen` 直接 `Permission denied`。
- **测试必须用宿主解释器**：python 依赖自带的解释器其 `_ctypes` 解析不到 libffi，
  会让套件在收集期就崩。
- **`cc` 问题不是"没装 cc"**：造 PATH shim 无效（posix_spawn 不搜 PATH），
  必须用 sitecustomize 补丁 Popen。
- **setuptools 不能靠 PYTHONPATH 供给**：PYTHONPATH 不执行 `.pth`，
  子环境的 distutils shim 会缺失（见 #8）。
---

**编译结束**: 2026-09-20 09:23
**最终状态**: built
