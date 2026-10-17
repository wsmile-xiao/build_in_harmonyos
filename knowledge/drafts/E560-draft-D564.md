# E560: 头文件暂定定义导致 clang/lld duplicate symbol

- **包**: cfingerd/1.4.3(通用模式,适用于一切 90 年代 C 代码)
- **类别**: linking
- **严重度**: major(阻塞构建)

## 现象

```
ld.lld: error: duplicate symbol: foo_utmp
>>> defined at main.c
>>>            main.o:(foo_utmp)
>>> defined at internal.c
>>>            internal.o:(.bss+0x0)
(每个包含该头文件的 .o 各报一次)
```

## 根因

旧代码在**头文件**里写 `struct utmp foo_utmp;`(暂定定义,tentative definition),配合 `#define UT_USERSIZE sizeof(foo_utmp.ut_name)` 推导平台相关的大小宏:

```c
#if !defined(UT_USERSIZE) || !defined(UT_HOSTSIZE) || ...
struct utmp foo_utmp;          // ← 暂定定义,每个 .o 一份
#endif
#ifndef UT_USERSIZE
#define UT_USERSIZE sizeof(foo_utmp.ut_name)
#endif
```

- 1990s gcc:多个暂定定义合并为一个 common symbol,链接通过
- clang(默认 `-fno-common`)+ ld.lld:每个 .o 都是强定义,直接报重复

**OHOS 触发组合**:鸿蒙 `utmp.h` 定义了 `UT_HOSTSIZE/LINESIZE/NAMESIZE` 但**不定义 `UT_USERSIZE`**,且 `#define utmp utmpx`(musl 风格)。`#if` 守卫因 `||` 逻辑必然为真 → 暂定定义必然编译 → 必然重复符号。

## 踩坑过程(为什么 extern 修补不收敛)

先尝试标准修法:头文件改 `extern struct utmp foo_utmp;`,在一个 .c 里提供定义。结果:
- `main.c` 的 `#if` 块因**包含顺序**(userlist.h 先 #define 了 UT_USERSIZE)被跳过,定义缺失
- 其他 .c 的宏状态不同,符号时有时无,nm 结果互相矛盾
- 头文件内宏展开顺序与 #include 顺序纠缠,修一处坏另一处

## 正确修复

**删除整个 foo_utmp 推导机制,用显式字面量替代**:

```c
/* 删除 #if 块和 extern,只留: */
#ifndef UT_USERSIZE
#define UT_USERSIZE 32          /* OHOS utmpx.h: ut_user[32] */
#endif
```

`UT_HOSTSIZE/LINESIZE/NAMESIZE` 平台已定义,`#ifndef` 自动跳过。一次修复,所有 .o 不再产生符号,无顺序依赖。

## 验证

```bash
make clean && make all CC=clang
nm src/*.o userlist/*.o | grep foo_utmp || echo "CLEAN"   # 无输出 = 修复
```

## 推广

grep 模式 `^struct \w+ \w+;` 出现在**头文件**里的,都是这个模式的候选。同类:BSD getutent 兼容层、旧 fingerd/who/w 家族软件。
