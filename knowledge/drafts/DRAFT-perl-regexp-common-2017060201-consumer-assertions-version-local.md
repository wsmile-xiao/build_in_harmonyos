# DRAFT-perl-regexp-common-2017060201-consumer-assertions-version-local

## 使用说明

当一个库在制品仓中**多版本并行**（如 perl-regexp-common 同时存在 2024080801 与
2017060201）时，test_package 的消费者功能断言**不能从其他版本的配方/测试/个人记忆
照抄**——上游在版本之间会改变模式注册名、默认语义、API 形状。本文给出"断言必须
对目标版本逐一实测"的操作流程。适用于任何多版本并行的库（不限 Perl）。

## 适用范围

- 场景：为旧版本目录新写 conanfile/test_package；同库递增版本后复制旧配方
- 对象：test_package 中的正例、**负例（unlike/die unless）断言**、模式/常量名引用
- 不适用：纯静态清单断言（文件存在性、版本号字符串）——它们本来就按版本写死

## 输入 / 输出定义

- 输入（风险信号）：
  1. 断言引用的名字在目标版本源码里 grep 不到（如 `$RE{zip}{American}` 在
     2017060201 中不存在，注册名是 `{US}`）
  2. 负例断言的"错误输入"在目标版本语义下其实是合法输入
     （2017060201 的 `$RE{list}` 默认允许空元素，`'a,,c'` 是合法匹配）
- 输出（流程）：每条功能断言在目标版本源码（或解包树）中找到依据后才允许进入
  test_package；找不到依据的负例一律删除而不是"顺手保留"

## 示例

照抄新版出错的断言（r1 真机失败）：

```perl
unlike('a,,c', qr/^$RE{list}$/, 'empty list element reject');   # 2017060201 默认允许空元素
like('12345', qr/^$RE{zip}{American}$/, 'US zip5 match');       # 该版本注册名是 {zip}{US}
```

正确流程（对 2017060201）：

```sh
# 1. 解包目标版本源码，确认注册名与默认语义
grep -n "American\|{US}"  Regexp-Common-2017060201/lib/Regexp/Common/zip.pm
grep -n "list"            Regexp-Common-2017060201/lib/Regexp/Common/list.pm
# 2. 每条断言在源码或上游 t/ 找到同款用法后再写入
```

审查清单：`grep -n unlike test_*.pl` 列出全部负例 → 每条反查目标版本语义 →
无依据即删。**宁可少一条负例，不可保留一条未验证的负例**（假失败会阻塞整个 CI）。

## 本轮证据

perl-regexp-common 2017060201 真机 shadow CI r1：功能 TAP 因上述两条照抄断言
exit 255；修正为 15 条经源码核实的断言后 r3 全过。
