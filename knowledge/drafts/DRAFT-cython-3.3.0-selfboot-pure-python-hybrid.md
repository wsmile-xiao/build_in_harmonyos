# DRAFT-cython-3.3.0-selfboot-pure-python-hybrid — Python C 扩展包的自举与签名

## 可复现症状与稳定错误签名

**症状 A（自举缺失）**：Cython 源码树里 `setup.py` 声明的扩展源是 `.pyx`，
但 sdist **不含预生成 `.c`**：
```
FileNotFoundError: [Errno 2] No such file or directory: 'Cython/Plex/Actions.c'
# 或 clang: error: no such file or directory: 'Cython/Compiler/Scanning.c'
```
稳定特征：`compiled_modules` 列表里的模块均为 `.pyx`，
且 `find <tree> -name '*.c'` 在包目录下命中为 0（仅 `Cython/Utility/*.c` 这类
被 include 的片段）。

**症状 B（签名缺失）**：构建成功但运行/测试时：
```
ImportError: Error loading shared library .../Cython/Compiler/Scanning.cpython-312-*.so: Permission denied
```
稳定特征：`Permission denied`（而不是 `cannot open shared object`）
——OHOS 上**外来 ELF 未签名**的 dlopen 语义（E212），文件权限位本身是正确的 755。

## 根因与最小复现

**根因 A**：Cython 是**自举**项目——它用 Cython 自己把 `.pyx` 编译成 `.c`。
PyPI sdist 为减小体积**不带预生成 C**（发布 wheel 才带）。
故构建前必须先有一个**能运行的 Cython**。

**关键洞察**：Cython 的 **纯 Python 形态自身即可当编译器用**（无需已编译的扩展）。
最小验证：
```bash
# 把未编译的源码树放进 PYTHONPATH，它就能编译 .pyx
PYTHONPATH=<cython-tree> python3 -c "
from Cython.Compiler.Main import compile, CompilationOptions, default_options
res = compile('m.pyx', options=CompilationOptions(default_options, output_file='m.c'))
print('errors =', res.num_errors)"
# -> errors = 0，m.c 约 309KB
```
这就是上游 `setup.py build_ext` 能工作的原理：
先以纯 Python 形态 import 自身，再把各扩展的 `.pyx` 转成 `.c`，
最后交给 C 编译器（clang）产出 `.so`。

**根因 B**：OHOS 的 ELF 执行/加载受 `.codesign` 段约束；
从 tar/wheel 解出的外来 `.so` 没有签名 → `dlopen` 被拒。
且 conan 的 `copy()` **会破坏已有签名**，所以签名时机必须是
**最后一次文件落位之后**。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 直接 `setup.py build_ext`（不加任何处理） | 失败——找不到 `.pyx` 对应的 `.c`（症状 A） |
| 设 `NO_CYTHON_COMPILE=true`（纯 Python 模式） | **构建通过**，但交付的是**未编译**（更慢）的 Cython；用于 scipy/sklearn 构建会显著拖慢，且失去本包作为 C 扩展编译器的加速价值 → **不采用** |
| 仅构建后签名一次 | 打包（`copytree`）后签名**失效** → 消费者 dlopen 报 Permission denied |
| 构建后签名 + **打包后再签名** | **通过，采用**（两次签名，第二次在 copy 之后） |

## 最终方案、输入输出与真实验证

**方案**（配方内三步）：
1. **自举构建**：`PYTHONPATH=<src> python3 setup.py build_ext --inplace`
   （纯 Python Cython 编译自身 `.pyx` → clang 编译 `.c`）；
2. **构建期签名**：遍历 `**/*.so`，`llvm-objcopy --remove-section .codesign`
   + `binary-sign-tool sign -inFile ... -selfSign 1`；
3. **打包后再签名**（`copytree` 之后），并断言包里确有 `.so`（载荷校验）。

**真实验证（2026-09-29，OHOS aarch64 / Python 3.12.9）**：
```
[cython build] build_ext rc=0
  -> Cython/_shared.*.so, Cython/Compiler/{Scanning,FlowControl,LineTable,Visitor}.so,
     Cython/Plex/{Actions,Scanners,Machines,Transitions,DFA}.so, Cython/Runtime/refnanny.so ...
# R34 消费者测试（打包布局）
compiled extensions load OK (Scanning, Scanners, _shared)      <- 签名有效
cython CLI transpiled demo.pyx -> demo.c (310588 bytes, real Cython output)
OK: packaged Cython works as a compiler (module + extensions + CLI)
```

**CLI 交付**：上游 `scripts=[...]` 装 `cython`/`cythonize`/`cygdb`。
本包不走 pip/setuptools 安装路径，而是把 `cython.py` 等拷到 `bin/` 下
并**改写 shebang** 指向 conan python 的绝对路径
（`#!/usr/bin/env python3` 在 OHOS 上不可靠）。
因 `bindirs` 非空 → **必须**在**软件级**提供 `commands.json`（R38/L0k）。

## 注意事项

1. **签名必须晚于所有 `copy()`**——这是 E212 族反复踩的点
   （lxml/pillow/gpgmepy/psutil 同款）。
2. **不要用 `NO_CYTHON_COMPILE=true` 图省事**：那会把"C 扩展编译器"
   退化成纯 Python 版，牺牲下游（scipy/sklearn）的构建性能。
3. 纯 Python 形态能否编译 `.pyx`，是判断"该包是否可自举"的**一秒判据**
   （见上最小验证）。
4. 同类形态：凡 `setup.py` 的扩展源是 `.pyx`/`.py` 且 sdist 不带 `.c` 的包，
   都要先备一个可运行的自身（自举），不能假设有预生成 C。
