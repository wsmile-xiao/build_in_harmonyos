# opalmod

Ola Lundqvist 的 Perl「库」集合 —— 提供 5 个相互独立又可组合的基础模块，
用于把常见的系统操作（查找可执行文件、读写文件、遍历目录、改写源码、日志/退出
控制）封装成简洁的 Perl 接口。

## Description

包含 5 个子模块：

| 模块 | 主要导出函数 | 用途 |
|------|-------------|------|
| `OpaL::where` | `which` | 在 PATH 中定位可执行文件 |
| `OpaL::read` | `readfile` / `readscalarfile` / `readfileline` / `readcommand` / `readscalarcommand` / `readcommandline` | 读文件与执行外部命令并取回输出 |
| `OpaL::dir` | `getdirlist` | 遍历目录取得条目列表 |
| `OpaL::manipulate` | `perlmodifyadvanced` / `perlmodify` / `perlmodify_insertafter` | 按规则改写 Perl 源码 |
| `OpaL::action` | `pdebug` / `action` / `cmdaction` / `exitlvl` / `setDebugLevel` / `getDebugLevel` / `setErrorHandler` | 日志、错误处理与退出码统一控制 |

## ⚠️ 它是 debarchiver 的硬前置

Debian 的 `control` 声明 `Depends: opalmod (>= 0.1.10)`；且 `debarchiver.pl`
在 **BEGIN 阶段**即 `use OpaL::action` —— 缺它连 `--version` 都无法执行
（实测 `Can't locate OpaL/action.pm` → `BEGIN failed`）。

故本包须**先行适配并发布**，`debarchiver` 才能适配。

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 0.2.2.1 | built | 2026-09-12 | 纯 Perl（无 XS）；`conan create` EXIT=0；上游自测原样 4/5 → 打必需补丁后 5/5 |

## OHOS 适配要点

| # | 要点 | 说明 |
|---|------|------|
| 1 | **纯 Perl，无 XS** | 实测 tarball 内 `.xs` 与 `.c` 文件数**均为 0** → 无需编译器，只有 `.pm` 要装 |
| 2 | **逐个驱动 5 个子模块** | 上游顶层 Makefile 仅用 `for` 循环驱动 5 个独立的 `Makefile.PL` 子目录；配方用 `self.run(cwd=OpaL/<part>)` 逐个执行，错误定位更清晰 |
| 3 | **用 `INSTALL_BASE` 而非 `DESTDIR`** | 指向 build 目录下的绝对 staging 路径，`make install` 直接落盘（与仓库既有 Perl 配方 Data-UUID 一致）|
| 4 | ★ **`PERL5LIB` 按实际位置反推** | MakeMaker 的落盘层级随 `INSTALL_BASE`/`INSTALLDIRS` 而变（`lib/perl5`、`lib/perl5/<version>`、`lib/perl5/<arch>/…`）→ 配方 glob 出 `OpaL/*.pm` 实际位置再取其上一级，避免"装好了但 Perl 找不到" |

## 依赖

**无外部依赖**（纯 Perl，仅用核心模块 `POSIX` / `Exporter` / `AutoLoader`）。

> 说明：仓库内既有 Perl 模块配方（Data-UUID、Devel-* 等 12 个）**均未声明**
> `perl` 作为 conan 依赖，本包沿用该惯例 —— Perl 解释器由构建/运行环境提供。

## Installation

```bash
conan create archives/o/opalmod/0.2.2.1 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 上游自测

5 个子模块各带 `test.pl`（Test::Harness 经典 `1..1` 协议）。

**上游原样 4/5** —— `OpaL::where` 失败；打上「必需补丁」（见下）后 **5/5 全过**。

## ⚠️ 必需补丁：AutoLoader 的 AUTOLOAD 未被 import

`OpaL::where` / `OpaL::dir` / `OpaL::manipulate` 三个模块把函数定义在 **`__END__`
之后**（靠 AutoLoader 按需加载），但**只把 `AutoLoader` 放进 `@ISA`，从未 import
其 `AUTOLOAD`**：

```perl
require Exporter;
@ISA = qw(Exporter AutoLoader);   # ← AutoLoader 只是"继承"，AUTOLOAD 没进来
```

现代 Perl（5.22+）已禁止"对非方法调用使用继承来的 AUTOLOAD"：

```
Use of inherited AUTOLOAD for non-method OpaL::where::which() is no longer allowed
```

→ 这些模块**能加载、但所有函数都无法调用**。`which` 是 `OpaL::where` 唯一的导出
函数，不修等于该模块完全不可用（`debarchiver` 依赖的 `OpaL::action` 恰好函数都在
`__END__` 之前，故未受影响 —— 这也解释了为何该缺陷长期未被上游发现）。

修法（`patches/0001-fix-autoloader-autoload.patch`）：在 `@ISA` 之前补一行

```perl
use AutoLoader qw(AUTOLOAD);
```
