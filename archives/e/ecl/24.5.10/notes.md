# ecl 24.5.10 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
ECL（Embeddable Common-Lisp）——可嵌入的 Common Lisp 实现，产出 `libecl.so` 与 `bin/ecl`。
是 Singular / SageMath / passagemath 计算代数栈的依赖（用作符号计算的 Lisp 后端）。

## 关键适配：两个补丁都是为了同一个 `bool`

### 0002 才是真因：`libraries.d` 把 `bool` 宏 undef 掉了

编译到 `src/c/ffi/libraries.d` 时一片：

```
ecl/internal.h:123:9: error: unknown type name 'bool'
ecl/threads.h:53:36: error: unknown type name 'bool'
```

诡异之处在于**全树两百多个 `.d` 文件只有这一个报错**，看起来像随机某个文件坏了。

真因：`libraries.d` 在 `#include <dlfcn.h>` 之后做了

```c
#  ifdef bool
#   undef bool
#  endif
```

（为清掉某些平台上 dlfcn.h 带进来的 `bool` 宏。）而 `<stdbool.h>` **有 include guard**——
`bool` 被 undef 之后，后面 `ecl/internal.h` 里再 `#include <stdbool.h>` 是**空操作**，
不会重新定义。于是 internal.h 与 threads.h 里所有 `bool` 全成了未知类型。

在把 `bool` 当关键字的工具链（C23）上恰好无碍；clang 15 默认 `-std=gnu17` 下是硬错误。

补丁 0002 在 undef 之后、include internal.h 之前按 C99 语义显式恢复：

```c
#if !defined(__cplusplus) && !defined(bool)
# define bool _Bool
#endif
```

### 0001 是卫生性修补

`internal.h` 自身用 `bool` 却不 include `<stdbool.h>`——正常路径下靠系统头链间接带进来
（全树没有任何源文件显式 include 它）。补上使该头自包含，不再依赖包含顺序的运气。

**注意**：只打 0001 不解决问题（已实测）——因为 0002 描述的 undef 发生在它之前。

### 其它
- 依赖 `gmp/6.3.0.1`（ECL 的 bignum 走 GMP）、`readline/8.3`、`gc/8.2.12`、`libffi/3.4.4`
- 删除 `lib/*.la`

## 真机验证（2026-08-12，HarmonyOS PC MateBook）
`conan create -pr ohos-native` 通过，test_package **4 条真实断言**全绿：

```
ecl: (*(+ 1 2)7)=21 通过；(expt 2 100) 位数=31 通过；闭包 funcall=144 通过；reduce=15 通过
```

测试把 ECL 当运行时**嵌进来**（`cl_boot` → 求值 → `cl_shutdown`）：

- `(* (+ 1 2) 7)` == 21
- `(length (format nil "~D" (expt 2 100)))` == 31 —— 走 ECL 内建 bignum（GMP）
- `((lambda (x) (* x x)) 12)` == 144 —— 真正过一遍求值器与调用约定
- `(reduce #'+ '(1 2 3 4 5))` == 15

**为什么不能只 dlopen**：ECL 的价值在于「真能起一个 Lisp 运行时」。
`cl_boot` 要初始化 GC、内建包与读取器，任何一环在鸿蒙上不成立，
`dlopen` 照样成功、符号也查得到，而一 boot 就崩。
