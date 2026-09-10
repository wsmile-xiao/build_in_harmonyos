# ═══ Draft knowledge entry — musl 无 TIOCGETA/TIOCSETA 且已预定义 TCGETA/TCSETA,termios 回退宏重定义致编译失败 ═══
# Timestamp: 2026-09-07
# Software: lci 1.1(所有在 termios 分支用 #define TCGETA TIOCGETA 回退的 C 代码)
# Gate: conan create build()
# Status: UNMATCHED — needs human/AI review to promote to E-entry

## 现象

OHOS(musl sysroot)下编译含终端 ioctl 回退段的 C 源文件失败:

```
src/run.c:76:11: error: use of undeclared identifier 'TIOCSETA'
```

同代码在 glibc(有 <termio.h>,走 termio 分支)与 macOS(termios 分支,
TIOCGETA/TIOCSETA 真实存在)均正常编译,极易误判为平台特有问题。

## 定位过程

1. 错误指向 `#define TCSETA TIOCSETA` 的使用点,而非定义点——说明宏展开
   引用了未声明标识符。
2. 检查 musl sysroot:`sys/ioctl.h` → `bits/ioctl.h` 中**已定义**
   `TCGETS=0x5405`/`TCSETS`(GNU 同名)、`TCGETA=0x5405`/`TCSETA=0x5406`
   (System V 名),但**不存在** `TIOCGETA`/`TIOCSETA`(BSD/macOS 名)。
3. 因此上游代码的无条件重定义 `#define TCGETA TIOCGETA` 在 musl 下是
   "把已有的正确宏改指不存在的标识符",编译器同时报宏重定义警告与
   未声明标识符错误。

## 根因

跨平台终端控制代码常见的平台选择结构:

```c
#if __has_include(<termio.h>)        // Linux/glibc
    #include <termio.h>
    typedef struct termio TERMIO;
#elif __has_include(<termios.h>)     // OSX and others
    #include <termios.h>
    typedef struct termios TERMIO;
    #define TCGETA TIOCGETA          // ← musl 下:TCGETA 已存在,
    #define TCSETA TIOCSETA          //   TIOCGETA 不存在 → 编译失败
#endif
```

musl 落入 termios 分支(glibc 落 termio 分支、macOS termios 分支的
TIOCGETA 真实存在),但该分支假设"没有 termio.h 的平台用 BSD 名
TIOCGETA/TIOCSETA",对 musl 不成立:musl 直接提供了 System V 名。

## 修复

用 `#ifndef` 守卫回退宏,仅在目标平台真缺 TCGETA/TCSETA 时生效:

```c
    #include <termios.h>
    typedef struct termios TERMIO;
    #ifndef TCGETA
    #define TCGETA TIOCGETA
    #endif
    #ifndef TCSETA
    #define TCSETA TIOCSETA
    #endif
```

对 glibc(macOS 走原路径)与 macOS(TIOCGETA 存在,宏仍生效)零行为
变化;musl 下直接使用 bits/ioctl.h 的正确值。

## 复用价值

- 任何 vendored/老 C 代码带 "termio/termios 双分支 + BSD 名回退宏"
  的包移植到 musl(OHOS/Alpine)都会命中;该模式常见于 REPL、终端 UI、
  字符级输入的老代码(lci 的 run.c 即此形态,2024 年上游仍如此)。
- 通用修复极小(#ifndef 守卫),portability patch 即可,不需要改构建系统。
- 与 knowledge 现有条目无重叠:E272 是 /bin/stty 与 tmpfile 部署问题,
  不涉及编译期宏;musl-compat 系列文档无 ioctl/termio 条目(已核对)。

## 验证

- lci 1.1 conan create(OHOS aarch64 profile):
  - 修复前:`error: use of undeclared identifier 'TIOCSETA'`(首个真实根因)
  - 修复后:编译 100%;上游定义4项测试;OHOS构建注册并执行3项
    (build/queens/fixed_point),3/3通过;条件性valgrind测试因目标环境无可用
    Valgrind而未注册;test_package 消费者测试 1/1(内部 7 断言) + 鸿蒙特有
    测试 1/1(内部 6 检查点)全通过(2026-09-07 首次验证;统计口径随
    2026-09-09 整改修订)
- 宏事实核对:`grep -rn "define TIOCGETA\|define TIOCSETA" <sysroot>/usr/include/`
  无结果;`bits/ioctl.h` 定义 TCGETA/TCSETA(musl 通用,非 OHOS 特有)。
