# DRAFT-perl-build-system-varies-and-class-inspector-semantics — CPAN 构建系统须逐包确认 + Class::Inspector 两处 API 语义

## 错误特征

**坑 ①：构建系统类推错误（不报错，但产出与上游偏离的构建入口）**

> 更强的反例：**同一软件的不同版本构建系统就不同**——class-inspector **1.30** 是
> Module::Install（`inc/` 随包 8 个文件）、**1.36** 是 Dist::Zilla 生成的普通
> `Makefile.PL`（直接 `use ExtUtils::MakeMaker`，**发行版内无 `inc/`**）。
> 两者都**无需**替换构建脚本，也都不适用 Module::Build 替换路径。

看到"纯 Perl 发行版"就按 Module::Build 系处理、生成替代 Makefile.PL。但若上游实际是
自带 Makefile.PL 的 **Module::Install**（引导随包在 `inc/`），则：

```
$ ls Makefile.PL inc/Module/Install.pm
Makefile.PL
inc/Module/Install.pm
$ perl Makefile.PL INSTALLDIRS=site     # 开箱可用，无需任何外部模块
Checking if your kit is complete...
Looks good
Writing Makefile for Class::Inspector
```

**坑 ②a：`subclasses()` 三态返回**

```perl
my $rv = Class::Inspector->subclasses('Class::Inspector');
# 若命中子类 → ARRAY ref；若无命中 → ''（空字符串）；若类名非法 → undef
```

按 ARRAY ref 一律断言：

```
not ok 18 - ->subclasses returns an ARRAY ref
```

**坑 ②b：非法类名喂给 `installed()`**

```perl
Class::Inspector->installed('4teen');   # 或 'Blah::%f' 等非法名
```

```
Use of uninitialized value $filename in hash element at .../Class/Inspector.pm line 235.
```

## 触发条件

- 坑 ①：适配任何**纯 Perl CPAN 发行版**时，未先核对源码根目录的构建清单
- 坑 ②：为 `Class::Inspector` 编写消费者/测试断言，且默认其返回类型单一
- 阶段：configuration（①，构建入口选择）/ testing（②，断言编写）

## 根因分析

### ① 纯 Perl 发行版至少有四种构建路径

| 形态 | 判据 | 适配做法 |
|---|---|---|
| ExtUtils::MakeMaker | 自带 `Makefile.PL`（直接 `use ExtUtils::MakeMaker`）| **沿用上游** |
| Dist::Zilla 生成 | 自带 `Makefile.PL`（注释含 `Dist::Zilla::Plugin::MakeMaker`）| **沿用上游** |
| **Module::Install** | 自带 `Makefile.PL` + **`inc/Module/Install.pm`** | **沿用上游**（引导随包）|
| Module::Build | 只有 `Build.PL`，`configure_requires Module::Build` | 生成等价 `Makefile.PL` |

关键点：**Module::Install 的引导随发行版打包在 `inc/` 内**，`perl Makefile.PL`
开箱可用——既不需要外部安装 Module::Install，也**不需要**生成替代构建脚本。
注意区分**有无 `inc/`**：

- 有 `inc/Module/Install.pm` → Module::Install（引导随包）
- 无 `inc/`、`Makefile.PL` 直接 `use ExtUtils::MakeMaker` → Dist::Zilla 生成的普通 MakeMaker

两者做法相同（沿用上游），但**不可据此推断同一软件的其他版本**。
只有"仅 `Build.PL`"的 Module::Build 系才需要替换（OHOS 无 `Module/Build.pm`）。

### ② Class::Inspector 的两处 API 语义

**`subclasses()` 三态** —— 上游实现：

```perl
@found ? \@found : '';      # 命中→ARRAY ref；无命中→''（非 undef）
# 而类名非法时：my $name = $class->_class( shift ) or return undef;   # →undef
```

**`_class()` 才是校验入口** —— `installed()`/`filename()` 会先经
`_inc_filename()` 取 `$INC{...}`，非法类名使其拿到 undef，于是产生取值警告。

## Recommended Solution

### 主方案（priority 1）— `per-distro-build-entry`

**① 适配前先列构建清单**

```bash
ls Makefile.PL Build.PL inc/Module/Install.pm 2>/dev/null
```

- 有 `Makefile.PL` → 沿用（无论背后是 MakeMaker / Dist::Zilla / Module::Install）
- 只有 `Build.PL` → 生成等价 Makefile.PL（逐项转写 `module_name`/`requires`/`test_requires`）
- 都没有 → 读 META/MANIFEST/Changes 判断，别强套模板

配方对"预期构建脚本缺失"**显式报错**，避免上游换构建系统时静默出错。

**② Class::Inspector 断言写法**

```perl
# subclasses 三态分别断言
my $rv = Class::Inspector->subclasses('Class::Inspector');
ok( ref($rv) eq 'ARRAY' and grep { $_ eq 'Class::Inspector::Dummy' } @$rv,
    '->subclasses finds the defined subclass' );
is( Class::Inspector->subclasses('Bad::Class'), '',     'no match → empty string' );
is( Class::Inspector->subclasses(''),           undef,  'invalid name → undef' );

# 类名校验走 _class()
ok(  Class::Inspector->_class('Class::Inspector') );
ok( !Class::Inspector->_class('4teen') );
ok( !Class::Inspector->_class('Blah::%f') );
```

命中场景需要先定义一个子类（上游 `t/02_main.t` 的 `Class::Inspector::Dummy`
同思路）：

```perl
BEGIN {
   package Class::Inspector::Dummy;
   require Class::Inspector;
   our @ISA = ('Class::Inspector');
   sub adummy1 { 1 }
}
```

### 回退方案（priority 2）— `inspect-upstream-changes`

既无 `Makefile.PL` 也无 `Build.PL` 时，读 `META.*`/`MANIFEST`/`Changes` 判断构建
系统；确属冷门系统（dub/meson/rake 等）→ 按其官方流程单独适配，或上报
`env_unsupported`（参见 gir-to-d 的 D 语言案例）。

### 禁止做法

- ❌ 「所有纯 Perl 包一律生成 Makefile.PL」——对 Module::Install/自带 Makefile.PL
  的发行版强加替代脚本，引入与上游不一致的构建入口
- ❌ `subclasses()` 一律按 ARRAY ref 断言——无命中返回 `''`、非法类名返回 `undef`
- ❌ 用非法类名调 `installed()`/`filename()`——触发 `_inc_filename` 的 undef 取值警告；
  校验请走 `_class()`

## 单库实证（2026-09-18）

| 项 | 实测 |
|---|---|
| class-inspector **1.30** 构建 | `Makefile.PL` + `inc/Module/Install.pm`（**8 个文件随包**）→ `perl Makefile.PL` 开箱通过，**无需替换** |
| class-inspector **1.36** 构建 | `Makefile.PL`（Dist::Zilla 生成，直接 `use ExtUtils::MakeMaker`）**无 `inc/`** → 同样**无需替换**；上游测试 `Files=6, Tests=86, Result: PASS` = **85 通过 + 1 用例 skip**（`t/class_inspector__inc_to_local.t` 的 Win32 分支），另有 **1 文件整体 skip**（`t/class_inspector__devel_hide.t`，缺 `Devel::Hide`）|
| class-inspector **1.30** 上游 t/（hnp perl 5.42.0）| `Files=4, Tests=80, Result: PASS` = **79 通过 + 1 用例 skip**（`t/03_inc_to_local.t` 的 Win32 分支；TAP 汇总行不显示 skip，只看 `Result: PASS` 会漏报）|
| 消费者断言修正前 | `not ok 18 - ->subclasses returns an ARRAY ref`，并伴 `Use of uninitialized value $filename` 警告 |
| 消费者断言修正后 | 1.30 = 29/29 全过；**1.36 = 30/30 全过**（均按三态断言 + `_class` 校验）|

## 测试覆盖边界

- 坑 ① 只解决"构建入口选择"；若上游构建系统本身在 OHOS 不可用（如仅 dub），
  不属本条，应走回退方案或 `env_unsupported`
- 坑 ② 只针对 Class::Inspector 的 `subclasses`/`_class` 语义；同类三态返回的其他
  模块需各自核实，不要一律套用
- 本条不涉及 `children`/`recursive_children`（上游未导出，`Functions.pm` 中已注释掉）

## 关联条目

- 相似：`E155`（纯 Perl + MakeMaker 构建需 `PERL5LIB`）、
  `DRAFT-perl-module-build-makemaker-substitution`（本条是它的"边界条件"：
  只有 Module::Build 系才需要替换）
