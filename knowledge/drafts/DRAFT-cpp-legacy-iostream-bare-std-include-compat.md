# DRAFT：旧 C++ 源码裸用 cerr/cout/endl → 现代 libc++ 全量 undeclared identifier

> 来源：xmacro/0.3pre-20000911（2000-09-11 快照）适配实测，2026-12-31

## 现象

`-DHAVE_IOSTREAM` 编译 2000 年代源码时，全部报错集中在 iostream 符号：

```
error: use of undeclared identifier 'cerr'; did you mean 'std::cerr'?
error: use of undeclared identifier 'endl'; did you mean 'std::endl'?
```

xmacro 三个 .cpp 合计 100+ 处，逐点打补丁不可维护。

## 根因

- 源码的 `#ifdef HAVE_IOSTREAM` 分支只切了头文件（`<iostream>`），没切用法；
- 老的 `<iostream.h>` 把流符号放全局命名空间，裸 `cerr` 天然可用；
- 现代 `<iostream>` 把符号收进 `std::`，没有 `using namespace std` 或 `std::` 前缀就全灭。

## 解法（force-include 兼容头，不改上游）

source() 末尾生成 `xmacro_compat.h`：

```c
#pragma once
#include <iostream>          /* 必须在前 */
using std::cerr; using std::cout; using std::cin;
using std::endl; using std::hex; using std::dec;
```

build() 编译命令统一加 `-include "<src>/xmacro_compat.h"`。

**关键坑**：`-include` 在翻译单元最前面注入，`std` 还未声明——兼容头里若漏掉
`#include <iostream>`，会报 `use of undeclared identifier 'std'`（实测踩过一次）。

## 实测证据

- 修复前：xmacroplay/xmacrorec/xmacrorec2 语法检查 3/3 失败（undeclared identifier）；
- 修复后：3/3 exit 0（仅剩 chartbl.h writable-strings、XKeycodeToKeysym deprecated 等历史告警）；
- 无补丁文件 → L4 天然 pass。
