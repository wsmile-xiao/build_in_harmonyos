# E581-draft-rjj666 — 共享库交付形态的 glibc 符号残留：静态库无恙、共享库必挂，LD_FLAGS 通道链入 PIC shim

> **Contributor**: rjj666 | **Status**: DRAFT | **Updated**: 2026-09-17
> **Severity**: 🟡 medium | **Category**: linking / libc / musl / shared-library / ohos

## 症状：构建全绿，消费者链接必挂

liblphobos/1.42.0（共享库版 Phobos + druntime）适配中，`conan create`
构建期全部通过，但任何一个消费者程序在链接阶段立即报错：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined:
        program_invocation_name
```

而**同源码**的 ldc/1.42.0 工具包（静态库形态）从未出现此问题。

## ★ 判别特征：同一符号残留，交付形态决定后果

glibc 特有符号 `program_invocation_name`（`core/internal/elf/dl` 模块引用，
用于读取进程名）在 OHOS musl 无实现。关键差异：

| 交付形态 | 引用它的 `.o` 命运 | 后果 |
|---|---|---|
| **静态库**（ldc 包） | 成员不被消费者拉入（无符号引用即不链接） | **无恙** |
| **共享库**（本包） | dl.o 被**整体打入** `.so`，符号进入动态符号表 | 消费者默认链接语义（`--no-allow-shlib-undefined`）下**必挂** |

一行判别（对每个交付的 `.so` 执行）：

```bash
nm -D --undefined-only libdruntime-ldc-shared.so.112 | grep program_invocation
# 有输出 = 残留，消费者必挂；无输出 = clean
```

**这是「静态库验证通过 ≠ 共享库交付安全」的直接反例**——问题不在构建期，
在消费者链接期爆发；本库构建验证全绿也发现不了。

## 为什么不能改源码

两条常规路线在本例全部失效：

1. **`__traits(compiles, ...)` 恒真**：D 侧 `PTHREAD_CANCEL_*` 等声明是普通
   声明，静态条件编译分支失效，无法用「编译期探测」回避；
2. **LDC 在 OHOS 不定义 `OHOS` 版本标识**（实测仅 `linux`/`Posix`/
   `CRuntime_Musl`，ldc 任务沉淀），无法 `version(OHOS) { __progname }`。

## 修复：经上游构建系统的共享库链接附加参数通道，链入 PIC shim

上游 `runtime/CMakeLists.txt` 暴露了 `LD_FLAGS` 变量
（语义："Extra C linker flags for shared libraries"）——这就是不改源码的
注入入口：

```bash
# ① shim 编为 PIC 对象（shim 同时提供 pthread_cancel 家族 no-op，E085）
clang -c -fPIC -o ohos_runtime_shim.o shim/pthread_cancel_shim.c

# ② 经上游官方参数通道链入每个 .so
cmake -S <src>/runtime -B <build> \
  -DLDC_EXE_FULL=<ldc2> -DDMDFE_MINOR_VERSION=112 -DDMDFE_PATCH_VERSION=1 \
  -DTARGET_SYSTEM="Linux;UNIX;musl" -DBUILD_SHARED_LIBS=ON \
  -DLD_FLAGS="<abs-path>/ohos_runtime_shim.o" ...
```

shim 内容（节选）：

```c
char *program_invocation_name = "";
char *program_invocation_short_name = "";
```

`.so` 自带定义后，消费者链接零符号错误——liblphobos test_package
消费者用例 **7/7 真机通过**。

### C/C++ 生态的等价通道

| 构建系统 | 通道 |
|---|---|
| Autotools | `LDFLAGS` |
| CMake（通用） | `CMAKE_SHARED_LINKER_FLAGS` |
| CMake（target 级） | `target_link_options()` / `target_link_libraries(<lib> PRIVATE <obj>)` |
| Meson | `link_args` / `link_with` |

泛化原则：**凡是上游构建系统暴露的「附加到共享库链接」的变量，都是不改
源码注入符号定义的通用入口。**

## 验证三步

```bash
# ① 交付前自查：每个 .so 的动态未定义符号表
nm -D --undefined-only <lib>.so | grep -E 'program_invocation|__libc_' || echo clean

# ② 确认 shim 确实进链（定义侧）
nm -D --defined-only <lib>.so | grep program_invocation

# ③ 消费者复验：默认链接语义编译一段引用该库的程序，要求零报错
```

## 适用范围

* 一切交付 `.so` 且内部引用 **glibc-only 符号**的库：
  `program_invocation_name`、`error_print_progname`、`__libc_*` 系列、
  `__ctype_b_loc` 等在 musl 无实现的 glibc 扩展；
* 典型触发场景：**同源码「工具包（静态库形态）已适配、库包（共享库形态）
  新适配」**——ldc → liblphobos 即此先例；日后任何 D/静态库生态拆分出
  共享库包时，此坑必然复现。

## 与既有条目的关系

| 条目 | 覆盖 | 本条差异 |
|---|---|---|
| `E493`（!5113） | 编译/链接期报 `program_invocation_name` undefined → **改源码用 `__progname`** | 本条覆盖**共享库交付形态**维度与**源码不可改时的构建系统通道**解法，互补不重复 |
| `E203` | `getprogname()`/`sys/poll.h` 的 musl 适配 | 同上，源码替换路线 |
| `E085` | musl 缺 pthread_cancel 家族 | 本条 shim 同文件附带其 no-op，配套使用 |

## 禁止的做法

**❌ 只在静态库场景验证通过（或只验证本库构建），即宣称共享库交付可用。**
静态库与共享库的符号暴露面完全不同；必须对每个交付的 `.so` 做
`nm -D` 未定义符号复核 + 消费者链接复验，否则问题在下游爆发。

## 诚实标注（limitations）

1. shim 提供的是**空串定义**：`core.internal.elf.dl` 读到的程序名为空串，
   功能不中断（与 ldc 包引导期适配同口径），但依赖真实程序名的行为
   （如诊断输出前缀）会弱化。
2. `--no-allow-shlib-undefined` 是 lld 对共享库链接的默认语义；若下游显式
   改用 `--allow-shlib-undefined` 可绕过，但不应以放宽下游链接语义为代价。
3. 未穷举 musl 缺失的全部 glibc 符号清单；`__libc_*`、`__ctype_b_loc` 等
   是否触发取决于库源码实际引用。
