# draft-delaunay-triangulation-2.1-meson-llvm-ar-native-file-injection

## 症状

MesonToolchain 构建的库在远端 CI（clean worker）`conan create` 的 meson
configure 期直接失败：

```
../meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]
Running 'llvm-ar --version' gave "[Errno 2] No such file or directory: 'llvm-ar'"
```

L1 fail，L2/L4/L5 skip，exit 1。同配方在本地真机可能通过（PATH 含工具链目录），
构成「本地绿、CI 红」的典型环境差异陷阱。

## 根因

conan `MesonToolchain.generate()` 只把 `c`/`cpp` 写进
`conan_meson_native.ini` 的 `[binaries]` 段，不写 `ar`/`ranlib`。meson
configure 期对 clang 工具链按裸名 `llvm-ar` 探测归档器：
- 本地真机 PATH 含 `/data/service/hnp/bin`，`llvm-ar` 可找到 → 本地通过；
- CI buildbot worker 是 clean 环境，PATH 与 CI profile 的
  `tools.build:compiler_executables`（仅提供 c/cpp）都探测不到 `llvm-ar` → 失败。

即：**配方依赖了执行环境的 PATH 差异**，不满足自包含。

## 修复

conanfile.py `generate()` 中，在 `tc.generate()` 之后补一段 ar/ranlib 注入：

```python
import os as _os
_ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
_ar = _ce.get("ar"); _rl = _ce.get("ranlib")
# CI profile 仅提供 c/cpp，未给 ar/ranlib：从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径
if not _ar:
    _cc = _ce.get("c") or ""
    _bindir = _os.path.dirname(_cc) if _os.path.sep in _cc else ""
    if _bindir:
        _cand = _os.path.join(_bindir, "llvm-ar")
        if _os.path.isfile(_cand):
            _ar = _cand
            _rlc = _os.path.join(_bindir, "llvm-ranlib")
            if _os.path.isfile(_rlc):
                _rl = _rlc
_nf = _os.path.join(self.generators_folder, "conan_meson_native.ini")
if _ar and _os.path.isfile(_nf):
    with open(_nf) as _f: _c = _f.read()
    if "\nar =" not in _c and "[binaries]" in _c:
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl: _ins += "ranlib = '%s'\n" % _rl
        _c = _c.replace("[binaries]\n", _ins, 1)
        with open(_nf, "w") as _f: _f.write(_c)
```

要点：
1. 优先读 `tools.build:compiler_executables` 的 `ar`/`ranlib`（显式配置优先）；
2. 缺失时从 `c` 编译器路径**同目录**推导 `llvm-ar`/`llvm-ranlib` 并用
   `os.path.isfile` 校验——clang 工具链的 ar 与其编译器同目录，不依赖 PATH；
3. 注入目标是 `self.generators_folder` 下的 `conan_meson_native.ini` 的
   `[binaries]` 段，仅写包自身生成目录，不污染 PATH、不改 CI profile；
4. 幂等：已存在 `ar =` 行则跳过，防止重复注入。

## 验证

1. 复跑 `python3 scripts/ohc-run.py conan-verify <name> <ver>`（G2 conan create
   全链 + test_package ctest）PASS；
2. 检查生成的 `conan_meson_native.ini` 实测包含
   `ar = '<full path>/llvm-ar'` 与 `ranlib = '<full path>/llvm-ranlib'`，
   并被 meson setup 成功消费；
3. 远端 CI（/rebuild）conan create 预期通过（clean worker 不再裸名探测）。

## 适用条件 / 反例

- 适用：一切用 `MesonToolchain` 构建、profile 的
  `tools.build:compiler_executables` 只给 c/cpp（未给 ar/ranlib）的库配方，
  且 clang 工具链目录内确有 `llvm-ar`/`llvm-ranlib`。
- 反例 1：autotools 库的 AR/RANLIB 缺失走 **E012** 环境变量方案
  （`AR=llvm-ar RANLIB=llvm-ranlib ...`），不套用 native 注入。
- 反例 2：cmake/静态库索引场景（**E385** cargo build.rs 等）机制不同，不套用。
- 反例 3：Windows host 的 meson cross file 补全（**E296**）是 host 侧
  `llvm-ar.exe` 场景，路径推导上下文不同。

## 七轴查重

| 轴 | 结论 |
|---|---|
| exact_duplicate | false — E481 为复合条目（ar/ranlib+TMPDIR+libm+ELF 签名），且无 `Unknown linker(s)` 签名 |
| causal_duplicate | 部分 — E481 root_cause (1) 同方向（profile 仅 clang → meson 找不到 ar/ranlib），但 E481 包裹在存档步骤失败中 |
| trigger_overlap | 部分 — 同为 clang-only profile + meson |
| solution_overlap | 高 — 同一机制：注入 ar/ranlib 进 conan_meson_native.ini [binaries]（similar_to=E481） |
| combination_novelty | false |
| boundary_novelty | true — configure 期 `Unknown linker(s): [['llvm-ar']]` + `Running 'llvm-ar --version' ... No such file` 探针签名、自包含修复不依赖 PATH |
| test_migration_novelty | true — conf 优先 + c 编译器同目录 isfile 推导写法可迁移至全部 MesonToolchain 配方 |

## 关系字段

- similar_to: E481, E012, E296
- caused_by: []
- prerequisite_of: []
- conflicts_with: []

## 边界与验证命令

```
验证命令: python3 scripts/ohc-run.py conan-verify <name> <ver>   # G2 PASS
签名复现: meson setup <builddir>  → ERROR: Unknown linker(s): [['llvm-ar']]
注入确认: grep -n -A2 '\[binaries\]' <build>/conan/conan_meson_native.ini
```
