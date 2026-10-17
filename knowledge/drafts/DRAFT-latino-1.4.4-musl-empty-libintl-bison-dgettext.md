# DRAFT-latino-1.4.4-musl-empty-libintl-bison-dgettext — musl 空壳 libintl.h + bison YY_→dgettext 序言：OHOS 编译期隐式声明错误，__GLIBC__ 能力守卫最小修补

- 触发事件：latino 1.4.4 适配，latparse.c 编译失败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-latino-1.4.4（草稿，未编号入库）

## 现象

OHOS aarch64（musl libc）下 conan create 编译 latino-core 的预生成
bison 解析器 `latparse.c` 报错：

```
latparse.c:2519:40: warning: call to undeclared function 'dgettext'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
      yyerror (&yylloc, root, scanner, YY_("syntax error"));
                                       ^
latparse.c:2519:40: error: incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *' [-Wint-conversion]
      yyerror (&yylloc, root, scanner, YY_("syntax error"));
                                       ^~~~~~~~~~~~~~~~~~~
```

同类错误出现在所有 `YY_(...)` 展开点（syntax error / memory exhausted /
cannot back up）。编译期即失败，尚未到链接。

## 根因（两层叠加，实证）

1. **bison 序言的手写映射**：上游 `latparse.y`/`latparse.c` 序言在
   `#ifdef __linux` 下写：
   ```c
   #ifdef __linux
   #include <libintl.h>
   #define YY_(Msgid) dgettext ("bison-runtime", Msgid)
   #endif
   ```
   OHOS clang 定义 `__linux`/`__linux__`（Linux 内核目标均定义），映射
   无条件生效——**不受 YYENABLE_NLS 守卫控制**（序言里的 `#define YY_`
   先于 bison 自带的 `#ifndef YY_` 守卫链，到达默认回退前已短路）。
2. **musl 的 libintl.h 是空壳**（实证）：
   - `cat $SYSROOT/usr/include/libintl.h` → 仅 `__USE_GNU_GETTEXT`
     宏定义，零函数声明；
   - `nm -D libc.so | grep dgettext` → 无符号（musl 不实现 gettext
     系列）；
   - 于是 `#include <libintl.h>` 成功但 `dgettext` 无声明 → 隐式
     函数声明（C99 起非法）→ `int` 传入 `const char *` 报
     -Wint-conversion。

glibc 下二者皆不成立：头文件声明齐全且 libc 自带 `__dgettext`/
`dgettext` 符号——上游在 Linux CI 一直正常。

## 与已有知识的区别（检索结论）

| 条目 | 阶段 | 机制 | 本草稿差异 |
|---|---|---|---|
| E015 | 链接期 | `undefined symbol: libintl_dgettext`，补 `-lintl` | 本例编译期即失败，头文件本身是空壳 |
| E027 | configure | NLS 探测失败，`--disable-nls` | 本例无 configure NLS 探测，CMake 直接编 |
| E531 | 编译期 | musl 缺 glibc 专有符号（qsort_r） | 本例头文件**存在**但为空壳，非符号缺失 |
| E020 | 编译期 | musl/glibc 符号差异 | 同上 |
| E092 | CMake | 无 HarmonyOS 平台模块 | 本例是 libc API 层，与 CMake 平台无关 |

结论：四类已有条目均不覆盖"musl 空壳头文件 + 编译期声明缺失"这一层，
确认为未覆盖的新通用根因。

## 可复用处置模式（配方内做，三步）

1. **定性**：读 sysroot 的 `libintl.h` 确认空壳（零函数声明），
   `nm -D libc.so` 确认无 dgettext 符号，排除 E015/E027/E531 覆盖；
2. **最小补丁**：预生成 `.c` 与 `.y` 序言**同步**把守卫收紧为
   `#if defined(__linux) && defined(__GLIBC__)`。`__GLIBC__` 是 libc 能力
   clang 预定义宏，非 OHOS Linux 不受影响；bison 默认恒等回退
   `#define YY_(Msgid) Msgid` 自然生效，错误消息按原文输出——musl 下
   dgettext 本就不可用，零功能损失；
3. **证据留痕**：conan create 双包 + 上游官方测试 + 消费者测试全过，
   `HMBS_UPSTREAM_TEST_RESULT` 如实记录。

补丁示例（conandata `patches:` + `patch_type: portability`）：

```c
-#ifdef __linux
+#if defined(__linux) && defined(__GLIBC__)
 #include <libintl.h>
 #define YY_(Msgid) dgettext ("bison-runtime", Msgid)
 #endif
```

## 安全边界与适用条件

- **适用**：Linux 内核 + musl（OHOS 及 musl 发行版）上，编译序言含
  `#ifdef __linux` → `dgettext` 映射的 bison 生成/手写代码；
- **不适用**：glibc Linux；链接期缺 `-lintl`（E015）；configure NLS
  探测失败（E027）；
- **限制**：若软件真依赖 dgettext 的**运行时翻译**（非 bison 消息宏），
  需评估移植 gettext 或禁用 NLS 功能路径，不能简单加守卫；补丁打在
  预生成 `.c` 时，若上游构建会重跑 bison（latino 不跑），必须同步补
  `.y` 序言，否则重新生成时回归；
- **副作用**：错误消息退化为英文原文（无翻译），可接受。

## 验证

latino/1.4.4 ohos-aarch64 conan create（shared/static 双包）：

- 打补丁后 latparse.c 编译通过；
- 上游官方测试 coverage.lat 1/1 通过（真机执行，exit=0）；
- test_package 3/3 通过（嵌入 API 全链 + CLI 10 项精确输出断言 +
  `--version`）；
- 日志：`~/latino-investigate/cc.log`、`~/latino-investigate/cc_static.log`；
- 配方：`archives/l/latino/1.4.4/`（conandata patches: 0001-musl-no-
  dgettext-in-bison-prologue.patch）。
