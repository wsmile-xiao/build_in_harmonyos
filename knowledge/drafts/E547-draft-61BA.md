# E547: Clang `.addrsig` 与 GNU as 文本汇编互操作

## 错误特征

Clang 默认生成文本汇编后，再交给不识别 LLVM `.addrsig` 指令的 GNU as，
汇编器会在该指令处退出：

```text
Assembler messages:
fixture.s:24: Error: unknown pseudo-op: `.addrsig'
```

## 触发条件

- 编译器是 Clang，流程包含 `clang -S` 或等效的文本汇编生成步骤。
- 后续汇编由 GNU as 完成，而不是 Clang integrated assembler。
- 常见于编译器、汇编器、链接器的互操作测试，普通的 `clang -c` 路径通常不触发。

## 根因分析

`.addrsig` 是 Clang 默认输出的地址重要性元数据指令。Clang 自带汇编器理解该
指令，但被选中的 GNU as 版本不解析它。问题发生在两个工具之间的文本格式边界，
不表示源 C/C++ 代码或目标指令编码有误。

## 解决方案

### 推荐方案

当 GNU as 本身就是被测工具时，通过构建系统把 `-fno-addrsig` 同时加入 C 与 C++
编译参数。该选项只让 Clang 省略地址重要性元数据，保留代码生成和 GNU as 的真实
执行路径；上游汇编测试仍然完整运行。

对于不测试 GNU as 的普通构建，可以保留 Clang integrated assembler，让同一工具链
消费自己的 `.addrsig` 指令。

### 禁止做法

- 不删除受影响的汇编器测试，也不把失败测试从测试清单中排除。
- 不在生成的 `.s` 文件上做临时字符串删除；参数应由配方或构建系统统一传入。

## 验证

```bash
printf 'int fixture(void) { return 1; }\n' > fixture.c
AS_BIN="${AS_BIN:-$(command -v as)}"
clang -S fixture.c -o default.s
if "$AS_BIN" default.s -o default.o; then
    echo 'default assembly unexpectedly passed' >&2
    exit 1
fi
clang -fno-addrsig -S fixture.c -o clean.s
"$AS_BIN" clean.s -o clean.o
```

期望第一个 GNU as 命令报告 `.addrsig` 解析错误并返回非零，第二个命令返回 0。
binutils 2.46.0 的独立探针得到该结果；随后 Conan 构建、五套 DejaGNU 汇总和
安装包消费者测试均完成。

## 关联条目

- E016：处理目标处理器不支持的汇编代码；其根因是指令集或汇编代码本身，与本条的
  编译器元数据格式边界不同。
