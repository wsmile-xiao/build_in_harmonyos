# cython 3.3.0 适配笔记

## 编译环境
- **类型**: Python **C 扩展**（自举编译）
- **编译日期**: 2026-09-29
- **Python**: 3.12（conan `python/3.12.9`）
- **编译器**: clang（OHOS SDK 26.0.0.18，aarch64-linux-ohos）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 为什么需要这个包
`Cython` 是 `scipy` 与 `scikit-learn` 的**构建期依赖**
（两者 `pyproject.toml` 的 `requires` 均含 `Cython>=3.x`）。
它是 sklearn 依赖栈的关键路径一环。

## 难点一：自举（bootstrap）
**sdist 不含预生成 C**——实测以下文件全部不存在：
```
Cython/Plex/Actions.c        Cython/Plex/Scanners.c
Cython/Compiler/FlowControl.c  Cython/Compiler/LineTable.c
Cython/Compiler/Scanning.c     Cython/Compiler/Visitor.c
Cython/Runtime/refnanny.c      Cython/_shared.c
```
而 `setup.py` 的 `compiled_modules` 列表（`Cython.Plex.Actions`、
`Cython.Compiler.Scanning`、`Cython._shared` 等十余项）都以 `.pyx` 为源。

**解决路径（上游标准自举）**：Cython 的纯 Python 形态**自身就能当编译器用**。
实测验证：把源码树放进 `PYTHONPATH` 后，
```python
from Cython.Compiler.Main import compile, CompilationOptions, default_options
```
可真实把 `m.pyx` 编成 `m.c`（309,796 bytes）——即用它自己把自身的 `.pyx`
编译成 `.c`，再交 clang 编译成 `.so`。

实测构建命令（`build_ext --inplace`）**成功**，产出全部扩展：
```
Cython/_shared.cpython-312-aarch64-linux-ohos.so
Cython/Compiler/Scanning.cpython-312-aarch64-linux-ohos.so
Cython/Compiler/FlowControl.cpython-312-aarch64-linux-ohos.so
Cython/Plex/Actions.cpython-312-aarch64-linux-ohos.so
Cython/Runtime/refnanny.cpython-312-aarch64-linux-ohos.so
... （共十余个）
```
**注意**：`setup.py` 的 `compile_cython_itself = not check_option('no-cython-compile')`
意味着**不要**设 `NO_CYTHON_COMPILE=true`——那会跳过编译、只交付纯 Python
（更慢）版本。本配方要的是编译版。

## 难点二：C 扩展必须签名（E212）
构建产出的每个 `.so` 在 OHOS 上是**外来 ELF**，未签名 `dlopen` 会
`Permission denied`（E212，psutil 适配时实证）。故本配方：
1. **build 期**签名一次（随后上游测试要真实 import，未签名会被拒）；
2. **package 期**再签一次——因为 conan 的 `copy()` 会**破坏 ELF 签名**
   （E212 族：lxml/pillow/gpgmepy 同款）。签名的正确时机是**最后一次文件落位之后**。

签名方式（pandoc/psutil 先例）：
```bash
llvm-objcopy --remove-section .codesign <f>
binary-sign-tool sign -inFile <f> -outFile <f>.signed -selfSign 1
```

## 难点三：CLI 入口与 shebang
上游 `setup.py` 的 `scripts = ["bin/cython", "bin/cythonize", "bin/cygdb"]`
会安装三个 CLI。本配方**不走 pip/setuptools 安装路径**（避免其构建路径
与 sed 干扰），而是手工把 `cython.py` / `cythonize.py` / `cygdb.py`
拷到 `bin/` 下的 `cython` / `cythonize` / `cygdb`，并**改写 shebang**
指向 conan python 包的绝对路径（OHOS 上 `#!/usr/bin/env python3` 不可靠）。

因 `bindirs` 非空 → 按 **PF8/R38 必须提供 `commands.json`**（已交付）。

## 上游测试（R51 如实申报）
`tests/` 下**不是 pytest 用例**：`tests/run/*.py` 是**由 `runtests.py`
编译执行**的 Cython 测试模块，直接 `pytest tests` 收集是错的
（实测 `Test*.py` 收集数为 0）。上游驱动方式是
```bash
python3 runtests.py -vv [selector]
```

本配方采取**两层证据**：
1. **端到端冒烟（会失败则 build 失败）**——用刚构建出的 Cython 把一个
   真实 `.pyx` 编成扩展并**真实调用**：
   ```python
   cythonize -i ohc_smoke.pyx      # add(int a, int b) -> a + b
   import ohc_smoke; assert ohc_smoke.add(20, 22) == 42
   ```
   这一条证明本包的**核心功能（当 C 扩展编译器用）真的可用**，
   而非仅"文件存在"。
2. **上游 runtests.py 限时子集**——如实记录；若超时则记录为"未完成"，
   **不谎报通过率**（R51：宁可申报未运行，不给虚假绿）。

## 关于 `commands.json` 的层级（PF8 vs PF9 的已知张力）
- **CI 的 L0k 是权威判据**：`ci/conan/build_and_test.sh` 里
  `PKG_SOFTWARE_DIR="$(dirname "$CONANFILE_DIR")"`、`COMMANDS_JSON="${PKG_SOFTWARE_DIR}/commands.json"`
  → **必须在软件级** `archives/c/cython/commands.json`。
  知识库条目 **E424** 亦明确："保持在软件级目录而不是版本目录"。
  仓内软件级 `commands.json` 有 **3156** 个先例（版本级仅 16 个）。
- **`scripts/ohc/preflight.py` 的 PF9 会对此误报**：PF9 的 `changed_files`
  取 `git diff base...head`，随后 `bad = [f for f in arch if len(f.split("/")) < 5]`
  ——软件级路径 `archives/c/cython/commands.json` 只有 **4 段**，必然命中。
- **实证这是系统性误报，非本包缺陷**：对仓内**已合并**的同类提交（如
  `lsd2` 新增 `archives/l/lsd2/commands.json`）跑同一 preflight，报**完全相同**的 PF9。
- **处置**：保留软件级 `commands.json`（满足 CI L0k 与 E424）；
  建 PR 时 PF9 这一条按已知误报处理（`--no-preflight` 或 PR 说明中注明），
  **不要**为了过 PF9 把它挪到版本级——那会让 CI L0k 失败（本末倒置）。

## 注意事项
1. **必须交付 `commands.json`**（有 bin/ 产物）——纯库包误加会被拦，
   有 CLI 的包不给也会被拦（PF8/R38 双向）；且**放软件级**（见上）。
2. `no-cython-compile` 开关：**不要**开启（见难点一）。
3. 签名必须在 `copy()` 之后（见难点二）。
4. 本包装的是 conan `python/3.12.9` 的 ABI——`requires("python/3.12.9")`
   已声明，消费者须用同一 python 包（C 扩展与解释器 ABI 绑定）。
