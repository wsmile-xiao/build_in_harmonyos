# DRAFT-test-refcount-import-and-refcount-semantics — CPAN 测试辅助模块的 import 语义与引用计数断言陷阱

## 错误特征

坑 ①（import 语义），两种错法各报一个错：

```perl
# 错法 A：把 @EXPORT_OK 的符号写进 use 的参数
use Test::Refcount qw( refcount );
```
```
plan() doesn't understand refcount at ... line 14.
BEGIN failed--compilation aborted at ... line 14.
```

```perl
# 错法 B：完全不带参数（只拿默认 @EXPORT）
use Test::Refcount;
...
my $n = refcount($object);
```
```
Undefined subroutine &main::refcount called at ... line 40.
```

坑 ②（引用计数断言的构造陷阱）：

```perl
my $var;
my $scalarref = \$var;
# 断言 refcount($scalarref) == 1
```
```
not ok 11 - SCALAR/ARRAY/HASH/CODE/GLOB refs each report refcount 1
```

## 触发条件

- 为 CPAN 测试辅助模块（`Test::*`）编写消费者断言，或直接使用 `@EXPORT_OK` 里的符号
- 用 `B::svref_2object(...)->REFCNT` 一类引用计数断言，且需精确控制词法槽位生命周期
- 阶段：testing（消费者测试编写期）

## 根因分析

### ① import 参数被当成 plan

`Test::Refcount` 与 `Test::More` 同族，都继承 `Test::Builder::Module`，其 `import`
会把**位置参数当 plan 参数**处理。因此：

| 写法 | 结果 |
|---|---|
| `use Test::Refcount qw( refcount )` | ❌ `plan() doesn't understand refcount`（编译期失败） |
| `use Test::Refcount;` | ⚠️ 只导入 `@EXPORT`（`is_refcount`/`is_oneref`），拿不到 `@EXPORT_OK` 的 `refcount` → 运行期 `Undefined subroutine` |
| `use Test::Refcount import => [qw( refcount )]` | ✅ 上游 POD 文档给出的正确形式 |

上游 `lib/Test/Refcount.pm` 的 POD 里就是这么写的：

```perl
use Test::Refcount import => [qw( is_refcount refcount )];
```

### ② 匿名引用的槽位仍在作用域

```perl
my $var;              # 词法槽位 $var 持有该标量
my $scalarref = \$var;  # 引用也持有 → REFCNT = 2
```

实测各类型起始引用数：

| 构造 | REFCNT | 说明 |
|---|---|---|
| `my $var; my $r = \$var;` | **2** | 槽位 + 引用 |
| `my $r = do { my $var; \$var };` | 1 | 槽位出作用域（上游写法）|
| `[]` / `{}` / `sub {}` / `gensym()` | 1 | 匿名，无槽位 |
| `qr/foo/` | **2** | 正则引用在现代 perl 起始即 2 |

上游 `t/04reftypes.t` 明确对 Regex 类型 skip：

```perl
if( $type eq "Regex" and $] >= 5.011 ) {
   # Perl v5.11 seems to have odd behaviour with Regexp references. They start
   # off with a refcount of 2. ...
   skip "Bleadperl", 1;
}
```

## Recommended Solution

### 主方案（priority 1）— `pod-import-form`

1. **导入**：取 `@EXPORT_OK` 的符号一律用 POD 的 `import => [...]` 形式；
   只有取 `@EXPORT` 默认导出时才可省略参数。
2. **构造**：标量匿名引用用 `do { my $var; \$var }` 隔离槽位；
   断言各引用类型时**不纳入 Regex**（上游已 skip）。

```perl
use Test::Refcount import => [qw( is_refcount is_oneref refcount )];

my $scalarref = do { my $var; \$var };   # refcount == 1
ok( refcount($scalarref) == 1, 'scalar ref refcount 1' );
```

### 回退方案（priority 2）— `call-fully-qualified`

不确定 import 形式时，直接全限定调用绕过导入语义：

```perl
my $count = Test::Refcount::refcount($object);
```

写法啰嗦但对任何 import 语义都安全，适合快速排障。

### 禁止做法

- ❌ 为让消费者断言通过而修改/删除上游测试、或放宽断言 —— 以掩盖换通过，违反 R51
- ❌ 对 Regex 引用断言 refcount == 1 —— perl 语义使然，上游已 skip；断言必失败，属假失败

## 单库实证（2026-09-18）

| 库 | 处理 | 结果 |
|---|---|---|
| test-refcount 0.10 | 消费者断言改 `import => [...]`；标量引用改 `do { my $var; \$var }`；不纳入 Regex | 正向 12/12 全过；失败路径 4 条诊断文案按上游语义核对通过 |

上游侧对照：`t/` 6 文件 20 用例在 hnp perl 5.42.0 下 `Result: PASS`。

## 测试覆盖边界

- 本条只覆盖**消费者测试的编写写法**（导入形式 + 引用计数构造），不改上游源码、不改上游测试。
- 若断言失败原因是 `B`/`Scalar::Util` 在目标平台行为异常（而非构造写法），不属本条。
- `import => [...]` 这一形式对 `Test::Builder::Module` 子类通用；对普通 `Exporter`
  模块仍可直接 `use Foo qw(...)`，不要盲目套用。

## 关联条目

- 相似：`E155`（纯 Perl + MakeMaker 构建需 `PERL5LIB`）
- 相关：`DRAFT-perl-module-build-makemaker-substitution`（同属 CPAN 纯 Perl 适配这一类）
