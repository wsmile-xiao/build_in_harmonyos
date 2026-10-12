# E-DRAFT: LLVM 22 llvm-lit 不再回退搜 PATH —— `use_clang(required=True)` 令整个套件首行 fatal（0 通过）

- **触发实例**：clang-format 22.1.8.src 适配（2026-09-18，分支 feat/clang-format-22.1.8.src）
- **错误签名**：`llvm-lit: .../subst.py:133: fatal: couldn't find 'clang' program`
- **类别**：test-harness-platform（测试基础设施平台差异）
- **严重度**：2（确定性失败，修复模式固定；但若误判会退化为“0 通过”而悄悄放过）

## 症状

用 `llvm-lit` 跑 `clang/test/Format`（或任何 `clang/test/*` 套件）时，首行即 fatal，
测试一条都没跑：

```text
llvm-lit: .../lit/llvm/config.py:...: fatal: couldn't find 'clang' program
# 套件报告 0 passed / 0 failed —— 不是“全过”，是“没跑”
```

## 根因

LLVM 22 的 `lit/llvm/config.py`：

```python
def use_llvm_tool(self, name, search_env=None, required=False,
                  search_paths=None, use_installed=False):
    if not tool:
        if search_paths is None:
            search_paths = [self.config.llvm_tools_dir]
        tool = lit.util.which(name, os.pathsep.join(search_paths))
    if not tool and use_installed:
        tool = lit.util.which(name, self.config.environment["PATH"])
    if required and not tool:
        self.lit_config.fatal(...)     # ← 套件配置期即中止
```

而 `clang/test/lit.cfg.py` 调 `llvm_config.use_clang()`，其 `required=True` 默认。
只构建 clang-format（不构建 `clang` driver）时，`bin/clang` 不存在 → fatal。

**LLVM 11 为何没这个问题**：旧版 `use_llvm_tool` 无条件搜 `config.environment['PATH']`，
设备 PATH 上的 hnp clang 恰好被命中（先例 clang-format-11/11.1.0 lit 21/21 通过的原因）。
LLVM 22 去掉该回退后，同一配方在同一设备上直接退化为 0 通过——纯工具链升级引起的回归。

## 修复

运行 `llvm-lit` 前设置环境变量 `CLANG`（`use_llvm_tool` 的 `search_env` 覆盖项，"use it
without validation"）：

```python
# R33：编译器从 conf 取，不裸用 shell 变量
_cc = self.conf.get("tools.build:compiler_executables")["c"]
os.environ["CLANG"] = _cc
self.run('cd "{}" && bin/llvm-lit -sv "{}"'.format(bdir, fmt_src))
```

对只跑 `clang/tools/*` 工具的套件（如 `clang/test/Format`）无副作用——这些用例不使用
`%clang`，仅调用被测工具本身；`FileCheck`/`count`/`not` 是 `use_default_substitutions` 中
`unresolved="fatal"` 的必需工具，需显式作为构建目标。

## 备选（不推荐）

把 `clang` 目标也加入构建：正确但昂贵（AArch64 上 clang-format 1777 步 → 含 driver 3175 步，
约翻倍）。除非套件确实需要新构建的 driver，否则优先用 `CLANG` 覆盖。

## 禁止

- 跳过 `clang/test/*` 套件，或把 `use_clang` 改成 `required=False` 去绕过 fatal（弱化/隐藏上游测试，R51）。
- 在配方里硬编码设备路径 `/data/service/hnp/bin/clang`（违反 R33，CI 不可移植）。

## 关联

- 实例配方：`archives/c/clang-format/22.1.8.src/conanfile.py`
- 相关：`DRAFT-22019-llvm-googletest-captured-stream-tmp-readonly`（同批 LLVM 22 测试基础设施差异）
