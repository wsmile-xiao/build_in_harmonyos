# DRAFT-autoloader-autoload-not-imported — AutoLoader 的 AUTOLOAD 未被 import：模块能加载，函数全不可用

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: perl / upstream-defect / packaging

## 症状

Perl 模块 `use` 得进去，但**调用它的任何导出函数都失败**：

```
Use of inherited AUTOLOAD for non-method OpaL::where::which() is no longer allowed
```

或（打包少了 `auto/` 树时）：

```
Undefined subroutine &OpaL::where::which called
Can't locate auto/OpaL/where/autosplit.ix in @INC
```

**关键陷阱：模块的 `use` 是成功的**。因此"能否加载"的断言会通过，问题只在真正调用
函数时才暴露 —— 而上游 `test.pl` 往往恰好只断言"`use` 成功"。

## 根因

`AutoLoader` 的机制是把 `__END__` **之后**的 sub 拆到 `auto/<Pkg>/*.al`，并由
AutoLoader 自己的 `AUTOLOAD` 在函数首次被调用时 `require` 对应文件。

```perl
# 上游写法（opalmod 的 OpaL::where / dir / manipulate）
require Exporter;
@ISA = qw(Exporter AutoLoader);   # ← 只是"继承" AutoLoader
                                  #    AUTOLOAD 并未进入本包的符号表
```

要让 AutoLoader 生效，本包符号表里必须有 `AUTOLOAD`，即必须显式 import：

```perl
use AutoLoader qw(AUTOLOAD);
```

- **旧版 Perl**：继承来的 `AUTOLOAD` 仍会被调用 → 掩盖问题
- **Perl 5.22+**：明确禁止对**非方法调用**使用继承的 AUTOLOAD → 抛错

上游代码写于 2002–2008 年，从未随 Perl 演进更新。

## 如何判定哪些模块需要修

按 `__END__` 行号切开，统计其后的 `sub` 数量：

```sh
for p in where read dir manipulate action; do
  e=$(grep -n '^__END__' OpaL/$p/$p.pm | cut -d: -f1)
  [ -n "$e" ] && echo "$p: $(awk -v s=$e 'NR>s && /^sub /' OpaL/$p/$p.pm | wc -l)"
done
```

opalmod 0.2.2.1 实测结果：

| 模块 | `__END__` | 其后 `sub` 数 | 需修 |
|------|-----------|--------------|------|
| **OpaL::where** | :75 | 1（`which`）| ★ 是 |
| **OpaL::dir** | :72 | 1（`getdirlist`）| ★ 是 |
| **OpaL::manipulate** | :78 | 3（`perlmodify*`）| ★ 是 |
| OpaL::read | :187 | 0 | 否 |
| OpaL::action | :270 | 0 | 否 |

> **上游测试只暴露了 `where`**（4/5）—— `dir`/`manipulate` 同样受影响，但它们的
> `test.pl` 只断言"模块可加载"，测不出。**靠消费者侧真实调用导出函数才发现**。

## 修法

### ① 补 import（`@ISA` 之前）

```perl
use AutoLoader qw(AUTOLOAD);
@ISA = qw(Exporter AutoLoader);
```

配方中改写后应**自校**该行确实生效，否则装出的是不可用的包。

### ② 打包必须带上 `auto/` 树

AutoSplit 在 `make` 阶段生成 `auto/<Pkg>/*.al` 与 `autosplit.ix`，**它们才是
`__END__` 后函数的实际载体**，且**不在源码 tarball 内**。

```python
# ✗ 只挑文件 → 装出"能加载、函数全找不到"的空壳
for pattern in ("*.pm", "*.so", "*.bs"):
    copy(self, pattern, src=staging, dst=dest)

# ✓ 整体拷贝 staging（含 auto/ 树）
copy(self, "*", src=staging, dst=dest)
# 并断言
if not glob.glob(os.path.join(dest, "**", "auto", "**", "autosplit.ix"), recursive=True):
    raise ConanException("缺少 auto/**/autosplit.ix —— AutoLoader 无法解析 __END__ 后的函数")
```

## 实证

**opalmod 0.2.2.1**（`feat/opalmod-0.2.2.1`，PR #9708）：

| 阶段 | 结果 |
|------|------|
| 上游自测（原样）| **4/5** —— `OpaL::where` 失败，报 `Use of inherited AUTOLOAD for non-method OpaL::where::which() is no longer allowed` |
| 补 `use AutoLoader qw(AUTOLOAD);` 后 | **5/5** |
| 首版配方（只拷 `*.pm`）| test_package 失败：`Can't locate auto/OpaL/where/autosplit.ix in @INC` |
| 改为整体拷贝 staging 后 | test_package **11/11** |

## 与既有条目的差异

| 既有条目 | 关系 |
|---------|------|
| `DRAFT-ohos-perl-script-package-conan-adaptation` | 讲的是 **shebang**（`env perl -w` 的 `-w` 陷阱）与 **conan perl 包内建 `@INC` 损坏**；本条讲 **AutoLoader 的 AUTOLOAD 未 import** 与 **`auto/` 树打包**，是 perl 适配的另外两个独立维度 |
| E404（zsh 5.9 missing autoload functions）| 讲的是 **OHOS 上 zsh 缺少 autoload 函数**（shell 层面）；本条是 **Perl AutoLoader 机制**，无关 |

> 查重（2026-09-12）：`AutoLoader` = **0**、`autosplit` = **0**、`uses AutoLoader qw(AUTOLOAD)` = **0**。
> `AUTOLOAD` 的 5 处命中分别在 E366（Emacs Lisp）与 E404（zsh autoload），**均不同题**（对 AutoLoader 命中为 0）。

## 禁止

- ❌ **只断言"模块能 `use` 成功"就认为测试通过** —— 本例的缺陷恰恰在"加载成功"之后；消费者侧必须**真实调用导出函数**
- ❌ **只改源码补 import、打包时仍只拷 `*.pm`** —— 函数载体会缺失，运行期报 `Can't locate auto/.../autosplit.ix`（两个问题独立，须都解决）
- ❌ **用 `no strict` / 忽略 `inherited AUTOLOAD` 警告来"绕过"** —— 那不是绕过而是**函数根本没被调用**；正确做法是 import 或直接把 sub 移到 `__END__` 之前
