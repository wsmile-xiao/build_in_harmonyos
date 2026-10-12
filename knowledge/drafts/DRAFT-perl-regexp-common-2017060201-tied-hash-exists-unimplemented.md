# DRAFT-perl-regexp-common-2017060201-tied-hash-exists-unimplemented

## 使用说明

在 Perl 消费者测试或功能脚本中对 **tied hash** 做存在性探测时（`exists $H{key}`），
如果 tie 实现没有定义 `EXISTS` 方法，程序会以
`Can't Regexp::Common::EXISTS`（或 `Can't <Package>::EXISTS`）直接崩溃（exit 255），
而不是返回假值。本文给出通用判定与替代写法。适用于编写/审查任何使用 tied hash
的 Perl 模块的 test_package 与功能断言。

## 适用范围

- 语言/运行时：Perl 5（实测 perl 5.42.0，aarch64 OHOS；旧版 perl 同样适用）
- 对象：任何 `tie my %H, 'Package'` 风格的模块。已知实例：`Regexp::Common` 的 `%RE`
- 场景：test_package 功能断言、上游测试补全、消费者冒烟脚本
- 不适用：普通 hash（非 tied）；tie 类实现了完整 `EXISTS`/`FIRSTKEY`/`NEXTKEY` 的模块

## 输入 / 输出定义

- 输入（症状）：日志出现 `Can't <TieClass>::EXISTS at <script> line N`，
  测试进程 exit 255，`Test::More` 报 "no plan was declared"
- 输入（代码特征）：断言中出现 `exists $tied{...}`、`defined exists`、
  `delete local` 等依赖 tie 元操作符的写法
- 输出（判定）：若该 hash 由 `tie` 创建且 tie 类源码无 `sub EXISTS` → 命中本条
- 输出（修复）：存在性探测改为「取值可用性探测」，用 `eval` 包裹，崩溃降级为失败断言

## 示例

命中写法（在 perl 5.42 + Regexp::Common 上必崩）：

```perl
ok(exists $RE{num}, '%RE{num} registered');   # Can't Regexp::Common::EXISTS
```

修复写法（tie 缺 EXISTS 时安全，探测真实可用性）：

```perl
ok(eval { $RE{num}{int}; 1 }, '%RE{num} usable');
ok(eval { $RE{URI}{HTTP}; 1 }, '%RE{URI} usable');
```

审查清单：对 `use Regexp::Common` / 其他 tie 模块编写的断言，grep `exists \$`
逐一确认 hash 是否 tied；是则改写为 eval 取值探测。

## 本轮证据

perl-regexp-common 2017060201 真机 shadow CI r2：
`Can't Regexp::Common::EXISTS at test_regexp_common.pl line 39`，exit 255；
改 eval 探测后 r3 该脚本 15/15 断言全过（job perl-regexp-common-2017060201-20261004）。

## 禁止做法

- 禁止给上游 tie 类补丁添加 `sub EXISTS` 来"修"测试——那是上游设计选择，补丁越界
- 禁止用 `no warnings 'uninitialized'` 掩盖取值失败——会把真失败变假通过（L1e 风险）
