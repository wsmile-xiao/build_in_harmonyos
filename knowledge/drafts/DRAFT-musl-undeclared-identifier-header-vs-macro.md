# DRAFT — musl 编译报 undeclared identifier 的两种根因分流：宏真缺失 vs 宏存在但头文件没引入

> 通用方法论条目（非单库补丁）。从 radioclk 1.0.pristine r1→r2 两轮真机
> 迭代提炼：r1 静态分析误判、r2 真机打脸的完整教训。

## 使用说明

当 OHOS/musl/aarch64 交叉编译报
`error: use of undeclared identifier '<标识符>'` 时，**先做本条目的二分诊断，
再选修复方案**。两种根因的修复方向完全相反，选错会多浪费一轮真机窗口：

| 根因 | 判据 | 正确修复 | 错误修复 |
|---|---|---|---|
| A. 宏在 musl 中**真不存在**（平台 ABI 差异） | sysroot 全量 grep 无 `#define <宏>` | 编译期能力守卫隔离分支（见 E567）；确认运行期降级路径 | ❌ 直接删调用点 |
| B. 宏在 musl 中**存在**，但在另一个头文件里（头文件布局差异） | sysroot grep 能找到 `#define <宏>`，但在没 include 的头中 | **补 `#include`**（找到真实定义头） | ❌ 加守卫（会把可用功能错误降级）❌ 伪造数值 |

关键陷阱：**"glibc 下能编译"不等于"没有隐式依赖"**。glibc 的头文件链
（如 `<termio.h>` → termios 系头）会间接引入大量宏和原型；只 grep 源文件
"是否使用该头自有符号"（如 `struct termio`）会漏判——代码可能依赖链上下文
里的**其它**符号（如 TIOCM_* modem 线宏）。静态分析判"死包含"必须连同
"该头在 glibc 上间接提供的所有符号"一起查，查不了就按根因 B 保守处理。

## 适用范围

- 平台：musl 系（OHOS/Alpine/裸 musl 交叉）目标，glibc/宿主机上历史代码正常编译
- 阶段：交叉编译 compilation
- 触发代码模式：vintage C（2000 年代及以前）、串口/终端/系统调用密集的工具型代码
- 构建系统：任意（cc/clang/make/cmake/autotools 均适用）
- **不适用**：标识符是代码自身笔误、或上游头文件漏发（那是源码 bug 不是 libc 差异）

## 输入输出定义

输入：
1. 编译错误中的标识符名（如 `TIOCM_CTS`）
2. 目标 sysroot 的 include 根目录（OHOS SDK 的 `sysroot/usr/include`）

诊断命令（在交叉编译环境或 SDK sysroot 上执行）：

```sh
# 根因分流：在 sysroot 中找定义位置
grep -rn "define TIOCM_CTS" <sysroot>/usr/include/
#   无输出            → 根因 A（真缺失）→ 走 E567 能力守卫
#   命中 termios.h 等 → 根因 B（头没引）→ 补 #include <termios.h>

# 顺带查函数原型（消除 implicit declaration 警告）
grep -rn "int ioctl" <sysroot>/usr/include/sys/ioctl.h
```

输出：
- 根因判定（A/B）+ 修复补丁（守卫 或 补 include）+ notes 中记录的功能影响说明

## 示例

radioclk 1.0.pristine（radioclkd.c，2003 年代码）r2 真机报 19 个
`undeclared identifier 'TIOCM_CD/TIOCM_CTS/TIOCM_DSR/TIOCMGET/TIOCMSET'`：

```sh
# 诊断：musl sysroot 中这些宏存在，位置在 termios.h
grep -rn "define TIOCM_CTS" <sysroot>/usr/include/   # → termios.h 命中
```

根因 B。上游 glibc 下靠 `#include<termio.h>` 的头文件链间接拿到这些宏，
musl 无 termio.h 且把 TIOCM_* 放 termios.h。修复（conanfile source() 内
replace_in_file）：

```diff
-#include<termio.h>
+#include<termios.h>     /* musl 的 TIOCM_* modem 线宏在这里 */
+#include<sys/ioctl.h>   /* ioctl() 原型，顺带消 implicit declaration */
```

反例（r1 的错误）：只 grep 了源文件无 `struct termio` 使用 → 判"死包含"→
直接删除 → r2 真机 19 个编译错。正确姿势是删除前先在**目标 sysroot** 查
"该头间接提供的符号是否被代码使用"。

同一文件中 `TIOCMIWAIT` 则是根因 A（musl 任何平台都不定义，x86 uapi 专属）
→ `#ifndef` 守卫 + 确认上游 `-p` 轮询降级路径，处理方式与 E567 一致。

## 验证

- 本诊断流程在 radioclk 1.0.pristine r2→r3 应用：r3 真机 shadow CI
  全绿（conan create 成功、L0/L1/L2/L4/L5 全 pass）。
- `verify_builds` 见同名 .kv。

## 关联条目

- E567 / E565：根因 A（宏真缺失）的能力守卫方法论与禁止事项（禁伪造数值）
- DRAFT-radioclk-1.0.pristine-musl-termio-tiocmiwait：本条目的原始案例
- E053 / E063：同类 undeclared 报错的非 libc 根因（编译器前端 / -Werror）
