# E430 — aarch64 上隐式函数声明截断指针/浮点（老 C 代码编译全绿但启动即 SIGSEGV）

## 错误特征

- 编译日志大量 `warning: implicitly declaring library function 'malloc' with type 'void *(unsigned long)'`、
  `call to undeclared function 'get_node'`、`call to undeclared function 'atof'` 等；
- 构建成功、无 error；
- 运行二进制立即 `Signal 11 (core dumped)`，或浮点相关输出为垃圾值。

## 触发条件

- 构建系统: make（K&R 时代的 makefile 最常见）
- 阶段: 编译期只出 warning，问题在 runtime 爆发
- 平台: aarch64（OHOS / arm64 Linux），x86-64 上也可能出现（浮点寄存器差异）
- 代码特征: 1992-2000 年的 K&R/ANSI C；标准头被放在发行版宏分支里
  （例：jgraph 83 的 `#ifdef LCC #include <stdlib.h> #endif`）

## 根因分析

C89 的隐式函数声明假定函数返回 `int`。对返回指针（`malloc`、链表 `get_node`）
或浮点（`atof`、`sin`、`cos`、`log`）的函数：

- 指针返回值在 aarch64 上是 64 位，被按 32 位 `int` 截断后使用 → 堆地址损坏、
  一启动就 SIGSEGV；
- 浮点返回值在浮点寄存器（d0），调用方却按 int 从通用寄存器读取 → 读到垃圾值；
- 该问题在 x86-64 上通常"侥幸"正常（调用约定差异），因此容易在移植时被忽略。

## 解决方案

### 推荐方案

1. 在主头文件**无条件**包含 `<stdio.h>`、`<stdlib.h>`、`<string.h>`、`<math.h>`，
   去掉 `#ifdef LCC`/`#ifdef VMS` 之类条件；
2. 为返回指针的自研函数补声明（如 `List get_node(List);`、`List make_list(int);`），
   声明放在所有使用方都会包含的头文件里；
3. 重新编译后用 `-Wimplicit-function-declaration` 复查：返回指针/浮点的函数
   不应再出现在隐式调用列表；
4. 用真实输入运行二进制做功能验证（本案例：`jgraph -P < simple.jgr` 输出 PS）。

### 禁止做法

- ❌ 用 `-Wno-implicit-function-declaration` 屏蔽后直接交付——截断仍然存在；
- ❌ 只对报错的调用点做强制类型转换——声明缺失时编译器仍按 int 生成调用。

## 验证

```bash
make CC=clang 2>&1 | grep -c "call to undeclared function"     # 危险函数应为 0
./jgraph -P < test_package/inputs/simple.jgr > /dev/null       # 真实运行不崩溃
```

## 关联条目

- 相关: E420（legacy C 隐式 int / 直接包含头文件）、E081、E093（libc 函数隐式声明）
