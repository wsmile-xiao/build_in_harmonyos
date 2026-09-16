# DRAFT-script-selflocate-layout-mismatch — 纯脚本包按 BASH_SOURCE 自定位时，安装布局必须与之一致

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: 🟡 medium | **Category**: packaging / bash / conan / testing

## 相关既有条目（同族差异化定位）

| 既有条目 | 同族点 | 本 skill 的增量（差异化） |
|---------|--------|--------------------------|
| **E043** | `$(dirname "${BASH_SOURCE[0]}")` 返回空 → 路径为空 | E043 是 **toybox sh 不支持 `${BASH_SOURCE}`**（解释器能力问题，改用 `$0` 等）；本条目是 **bash 下 BASH_SOURCE 正常工作、推导结果正确，但安装布局与之不匹配**（打包问题）——症状与修法完全不同 |
| **DRAFT-m1ddc-apple-ddc-transport-boundary** | 均提及"假成功" | 该条是**运行时不应返回假成功**（DDC 无真实 transport）；本条目是**测试侧假成功**（存在性断言 + 无效环境变量掩盖布局缺陷） |
| **DRAFT-bats-suite-ohos-runtime-shims** | 同属 bork 适配产出 | 该条讲如何让 bats 套件跑起来（框架装配）；本条讲**交付包布局正确性**与测试可信度，是另一个维度 |

> 查证（2026-09-11）：`自定位` / `script self-locating` / `不读环境变量` /
> `vacuous` 命中 **各 0 条**；`BASH_SOURCE` 命中 3 条但均为 E043 系
> （解释器不支持），**无条目覆盖"布局与自定位推导不匹配"**——本条为空白。

## Scope（何时用）

打包**纯脚本 / 无编译包**（bash/sh/Python 工具 + 伴随 lib 模块）时。典型现象：

```
$ <pkg>/bin/bork version
.../lib/helpers/md5cmd.sh: No such file or directory     # 交付包不可用
```

而 CI 却是绿的——因为 `test_package` 只断言了"文件存在于某处"。

## 根因（两类问题互为因果）

### ① 交付包缺陷（主因）：布局 ≠ 脚本自定位推导

可执行脚本常按自身路径定位伴随模块：

```bash
# bin/bork
BORK_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"   # → <pkg>
source "$BORK_SOURCE_DIR/lib/helpers/"*.sh
source "$BORK_SOURCE_DIR/lib/declarations/"*.sh
source "$BORK_SOURCE_DIR/lib/support/"*.sh
```

**该推导结果由安装布局决定，且脚本通常不读任何环境变量来覆盖它。**
但很多 conanfile 的 `package()` 按"惯例"把模块装到 `share/<pkg>/`：

```python
libdir = os.path.join(self.package_folder, "share", "bork")   # ✗ 与脚本预期不符
```

→ 交付包运行时直接报 `No such file or directory`。**包是坏的，只是文件都在。**

### ② 测试假成功（放大因素）：存在性断言 + 臆造环境变量

```python
env["BORK_HOME"] = libdir          # ✗ 脚本根本不读这个变量
r = subprocess.run([bash, bork, "--help"], ...)
if os.path.isdir(os.path.join(pkg, "share", "bork", d)):   # ✗ 只查"存在"
```

两个毛病叠加：注入了不起作用的变量 + 只做存在性断言 → **测试通过，缺陷被掩盖**，
一路通过 CI 直到消费者踩到。

## 方案（两步必须同时做）

### ① 对齐安装布局到脚本预期

先读主脚本的自定位表达式，确定它期望的基准目录（如 `bin/` 的上一级 = `<pkg>`），
再把伴随模块装到该路径：

```python
# conanfile.py
src_lib = os.path.join(self.source_folder, "lib")
libdir = os.path.join(self.package_folder, "lib")        # ← 与 BASH_SOURCE 推导一致
for d in os.listdir(src_lib):
    if os.path.isdir(os.path.join(src_lib, d)):
        os.makedirs(os.path.join(libdir, d), exist_ok=True)
        copy(self, "*", src=os.path.join(src_lib, d), dst=os.path.join(libdir, d))

def package_info(self):
    self.cpp_info.bindirs = ["bin"]
    self.cpp_info.libdirs = ["lib"]     # 同步，避免下游按错误目录取文件
    self.cpp_info.resdirs = ["lib"]
```

### ② 让 test_package 真实执行

- **删掉脚本不读的环境变量**（写之前先在源码里 grep 确认该变量确实被读取）；
- 改为**真实运行一个能退 0 的子命令**并断言输出：

```python
r = subprocess.run([bash, bork, "version"], capture_output=True, text=True, timeout=60)
if r.returncode != 0 or "bork" not in r.stdout:
    return 1        # 真实执行 + 输出断言，而非存在性
```

> ⚠️ 选命令有讲究：bork 的 `--help` 走上游 `case` 兜底分支，打印用法后 **`exit 1`**
> （设计行为，非错误）——用它断言会误判。应改用 `version`（退 0 并输出版本号）。

### ③ 自检手法（验证测试是否真的可信）

**故意把模块放错目录，重跑测试**：

| 结果 | 结论 |
|------|------|
| 测试 **FAIL** | ✅ 测试有效，能抓出布局缺陷 |
| 测试仍 **PASS** | ❌ 断言仍是存在性 / 环境变量型假成功，**必须先修测试** |

## 备选（fallback）

`install-both-layouts-plus-wrapper`：若上游脚本对布局的假设不可靠（多版本推导基准不一），
可在保持脚本预期路径为主的同时，在兼容路径放**符号链接**（而非复制），并保持
`package_info` 指向真实路径。这是妥协方案，**仍须以"真实执行通过"为验收标准**。

## 禁止

- ❌ **只做存在性断言**（"模块已打包"）：文件存在 ≠ 脚本能找到它。存在性断言 + 错误
  布局是假成功的标准配方。
- ❌ **注入脚本不读的环境变量**让测试通过：不改变任何行为，只制造"看起来通过"。
- ❌ **未确认真实加载路径就照搬惯例布局**（如一律装 `share/<pkg>/`）：布局正确性由脚本
  自身推导逻辑决定，不由惯例决定；照搬会把别的包的布局错误复刻过来。

## 实证

- **bork/0.14.0（PR #8710）**：
  - 缺陷：`package()` 装到 `share/bork/`，而 `bin/bork` 只读 `<pkg>/lib/` → 交付包不可用；
  - 掩盖：旧 `test_package` 注入 `BORK_HOME`（脚本不读）+ 仅存在性断言 → CI 通过（假成功）；
  - 修正：布局改为 `<pkg>/lib/` + 测试改为真实执行 `bork version` 并断言版本号；
  - **自检**：把模块放到旧 `share/bork/` 布局重跑 → 测试 **FAIL**（证明测试现在能抓出该缺陷）。
