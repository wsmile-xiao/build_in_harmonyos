# DRAFT：share 数据文件定义的宏指令——xfpt 类 DSL 工具的 test_package 转换断言要点

> Draft（未 promote）— 来源于 xfpt 1.00 真机 shadow CI（job xfpt-1.00-20260929，r3，2026-09-29）
> 对应 `.kv` 文件同 stem：`DRAFT-xfpt-1.00-consumer-test-runtime-datafile-macros.kv`

## 症状

真机上 xfpt 二进制本身工作正常（--version/-help/错误路径断言全 PASS），
test_package 的 DocBook 转换断言却失败：

```
** Error: unknown directive line: .docbook
   Detected near line 2 of t.txt
** Error: unknown directive line: .book
** Error: unknown directive line: .chapter "Test chapter"
```

测试输入（看起来很合理的最小样例）：

```
.include stdflags
.docbook
.book
.chapter "Test chapter"
This is a paragraph with &*bold*& text.
```

## 根因

xfpt 的 `.docbook` / `.book` / `.chapter` / `.section` 等**结构指令不是
编译进二进制的内建 directive**，而是上游 share 数据文件 `stdmacs` 中定义的
宏（`stdflags` 只定义 `&*bold*&` 这类 flag 展开）。测试输入缺
`.include stdmacs`，指令集不完整，第一个结构指令就报 unknown directive。

报错文本 "unknown directive line" 有很强的误导性——看起来像二进制功能损坏
或移植缺陷，实际是**测试输入没携带上游分发的运行时数据文件**。

## 方案（四条要点）

1. **include 组合必须复刻上游**：从上游 `testing/infiles` 挑最小样例时，
   保留其完整 include 组合（xfpt 的样例都是 `stdflags` + `stdmacs` 成对），
   不要凭直觉裁剪——缺一个 include 就改变可用指令集语义；
2. **显式绑定包内数据目录**：`xfpt -S <pkg>/share/xfpt`，顺带验证
   share 数据打包完整性（消费测试实质依赖被测包产物）；
3. **期望输出从上游 outfiles 原样摘取**：`<?xml version="1.0"?>`、
   `<!DOCTYPE book`、`<book>`、`<emphasis role="bold">bold</emphasis>`、
   `</book>` 等断言片段来自 `testing/outfiles/01`，不要手写猜测；
4. **分辨指令来源再下结论**：报 unknown directive → 先查该指令定义在
   share 数据文件还是源码内建，再判断是移植缺陷还是输入缺依赖。

修复后 xfpt r4 轮全绿（上游测试 7/7、test_package 6/6、L0-L5 全 pass）。

## 复用面

一切**带运行时数据目录（share/）的 DSL/宏处理器类工具**的 test_package
设计：Philip Hazel 系工具（xfpt、aspic、sdop）及类似 groff/tex 生态的
转换工具。核心教训通用：**DSL 工具的能力一半在二进制、一半在数据文件，
消费测试必须同时覆盖两者**。
