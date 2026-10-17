# 判定上游测试须按「该语言的生态惯例」——D 的 unittest 在源码里，不在 t/ 目录

**草稿 ID**: `DRAFT-test-discovery-per-language-convention`
**来源 PR**: #10885（gir-to-d 0.23.3 适配）
**日期**: 2026-09-18

---

## 一句话结论

「上游测试在哪」**没有跨语言统一答案**。按上一个项目的目录结构去找（尤其刚从
Perl/autotools 切过来时，`t/` + `prove` 印象太深），会得出「**找不到 → 上游没有
测试**」的误判——而这个误判**不会报错**，会一路写进 MANIFEST、通过率栏和 PR 描述。

> **配套结论**：上游**有**测试但**未接入构建流程**时，那是「跑不了」，**不是「不存在」**。
> 两句话的证据强度与后续动作完全不同。

---

## 错误特征

**坑 ①：只找一种布局就下结论**

```bash
$ ls t/ tests/ test/          # 全都没有
$ echo "上游无自动化测试套件"   # ← 误判从这里开始
```

D 的测试**根本不在这里**——它内嵌在源码模块里。

**坑 ②：误判静默通过全部门禁**

`MANIFEST.yml` 写 `upstream_tests: []`、通过率写「不适用」——
CI 的 L0e **只校验该文件存在**，不校验内容真伪。于是漏报一路通过。

**坑 ③：把「未接入」说成「不存在」**

三条构建路径都没有 test 目标，很容易顺手写成「上游无测试」。但真相是
**测试存在，只是没人驱动它们**。

**坑 ④（同源错误）：按生态惯例推测元数据**

同一 PR 里我把许可证按生态惯例猜成 Boost（gtk-d 生态看着像），实际是 LGPL v3。
**惯例可以提示方向，但不能替代读上游 `COPYING` / 元数据。**

---

## 根因

「上游测试在哪」由**语言 / 构建生态的惯例**决定：

| 语言 | 测试位置 | 驱动方式 |
|---|---|---|
| **D** | **源码内嵌 `unittest` 块** | `dub test`（即 `-unittest` 编译）|
| Rust | 源码内嵌 `#[cfg(test)] mod tests`，另可 `tests/` | `cargo test` |
| Go | 同目录 `*_test.go` | `go test` |
| Python | `tests/`、`test_*.py` | `pytest` |
| Perl | `t/*.t` | `prove` / `make test` |
| Node | `test/`、`__tests__/` | `package.json` 的 `scripts.test` |
| Java | `src/test/java` | maven / gradle `test` |
| C/C++ | 依构建系统 | `make check` / `ctest` / `meson test` |

**把某一种布局当通用默认，就必然在其他语言上漏判。**

第二层成因是**语义混淆**：上游有测试但构建系统未接入（`GNUmakefile` 无 test 目标、
`meson.build` 无 `test()`、`dub.json` 无 `-unittest`）时，「跑不了」被表述成
「不存在」。

---

## 正确做法：三步，缺一不可

### ① 按该语言惯例**穷举**候选（不能只查一种）

```bash
# 目录型
find . -iname 't' -o -iname 'test*' -o -iname 'spec' -o -iname '*_test.*'
# 源码内嵌型
grep -rn 'unittest\|#\[test\]\|func Test\|def test_\|describe(' --include='*.<ext>' .
```

### ② 查构建系统是否接入

```bash
grep -n 'check\|test' Makefile GNUmakefile meson.build CMakeLists.txt package.json
```

有 test 目标 = 可经该路径跑；**无 = 需手工驱动，但测试仍存在**。

### ③ **实跑一次**取真实通过/失败数

D 的等价驱动（排除自带 `main` 的入口文件）：

```bash
ldc2 -I<ldc>/include/d -I<src> -L-L<ldc>/lib -unittest -main \
     -of=ut <src>/source/gtd/*.d && ./ut
```

> **判据：能跑到具体的通过/失败数才算数。`ls` 没看到目录，不构成「无测试」的证据。**

### 申报时严格区分三种状态

| 状态 | 怎么写 |
|---|---|
| **有且已接入** | 如实报通过率（如 `85/86 通过 + 1 skip`）|
| **有但未接入** | 列出块数/断言数 + 给出等价驱动命令 + 注明 `upstream_test_in_build=false` |
| **确实没有** | 须给出**已穷举的证据**，而非仅「没找到 `t/`」|

---

## 禁止做法

| # | 禁止 | 原因 |
|---|---|---|
| 1 | 仅因「没找到 `t/`」就把 `upstream_tests` 置空、通过率填「不适用」 | 把未发现当成不存在，属 R51 漏报；L0e 只校验文件存在，不会替你发现 |
| 2 | 未穷举即断言「上游无测试」 | 结论无证据支撑；一旦复核即被推翻，需返工全部文档与 PR 描述 |
| 3 | 按生态惯例**推测**许可证等元数据 | 惯例可提示方向，不能替代读 `COPYING` / 包元数据（`dub.json` 的 `license`）|

---

## 兜底方案

若语言/构建生态冷门、驱动方式确实无法确定，就**如实申报为「未能确认」并附穷举
证据与已尝试的驱动方式**——**不要填「不适用」，也不要填「0」**。
把「不知道」写成「没有」，正是本条要防的主要错误。

---

## 本次实证（gir-to-d 0.23.3）

初版按 Perl 惯例只找 `t/`，漏报「上游无测试」。复核后真相：

| 位置 | 断言数 | 实测 |
|---|:---:|---|
| `source/gtd/GirVersion.d:148` | 8 | ✅ 8 PASS |
| `source/gtd/GirWrapper.d:826` | 2 | ⚠️ 1 PASS + 1 FAIL |
| `source/gtd/GirWrapper.d:883` | 1 | ✅ 1 PASS |
| `source/gtd/XMLReader.d:436` | 1 | ❌ 1 FAIL |
| **合计** | **12** | **10 PASS + 2 FAIL** |

- 上游 master 全树 **26 个文件**：无 `t/`、无 `tests/`、**也无 `.github/workflows`**
  —— 测试**只**以源码内嵌 `unittest` 形式存在。
- 2 处失败为上游既有缺陷（`stringToGtkD` 误改写参数中的 `string`；
  `ByChar.front` 对空 `data` 取 `[0]`），**与本配方无关**
  （失败模块不引用被补丁文件，上游 master 同一断言未变）。
- 上游**未把测试接入任何构建路径**，故 `upstream_test_in_build=false`；
  若计入，上游通过率为 **10/12**。

**教训**：「未接入构建流程」应写成 `upstream_test_in_build: false` + 列出真实用例数，
而**不是**写成「上游无测试」。

---

## 适用与关联

**适用**：所有需按 R51 申报上游测试口径的适配任务，尤其非 C/C++ 系语言。

**关联**：
- `similar_to: [E155, DRAFT-perl-makefile-gated-test-skip-all, DRAFT-d-language-toolchain-ohos-gap]`
- `DRAFT-perl-makefile-gated-test-skip-all` 是「**跑了但被 skip**」的假绿（分母被
  悄悄缩小）；本条是「**根本没找到**」的漏报。二者互补，共同构成测试申报的两类失真。
