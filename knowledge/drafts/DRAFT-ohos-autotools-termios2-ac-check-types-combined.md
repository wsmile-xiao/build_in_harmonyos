# OHOS autotools termios2 特征检测需"类型+ioctl 常量"组合验证

> 知识草稿（候选观察）| 来源: libmodbus 3.2.0 适配 | 2026-09-09
> 对应 .kv: `DRAFT-ohos-autotools-termios2-ac-check-types-combined.kv`

## 问题

libmodbus 3.2.0 在 HarmonyOS PC (aarch64) 上编译报错：

```
modbus-rtu.c:695:23: error: use of undeclared identifier 'TCGETS2'
modbus-rtu.c:911:23: error: use of undeclared identifier 'TCSETS2'
modbus-rtu.c:917:23: error: use of undeclared identifier 'TCGETS2'
modbus-rtu.c:1187:27: error: use of undeclared identifier 'TCSETS2'
4 errors generated.
```

## 根因

上游 `configure.ac` 使用 `AC_CHECK_TYPES([struct termios2], [], [], [[#include <asm/termbits.h>]])`
只检测 `struct termios2` **类型**是否存在。OHOS sysroot 的 `asm/termbits.h` 提供
`struct termios2`（因此 `HAVE_STRUCT_TERMIOS2=1` 被定义），但**不定义
`TCGETS2`/`TCSETS2` ioctl 常量**，导致 `#ifdef HAVE_STRUCT_TERMIOS2` 选中的
termios2 代码路径全部编译失败。

本质：特性检测不完整——"类型存在"不等于"配套 ioctl 常量存在"。
与既有 `DRAFT-ohos-termbits-termios-fallback-knob`（bootterm 的 NO_TCGETS2
开关注入）根因同族，但 libmodbus **无上游编译期开关**，必须修 configure 检测本身。

## 方案

将 `configure.ac` 的类型检测替换为组合编译检测（AC_CACHE_CHECK + AC_COMPILE_IFELSE），
同一测试程序同时引用 `struct termios2`、`TCGETS2`、`TCSETS2`，三者齐备才定义
`HAVE_STRUCT_TERMIOS2`：

```m4
AC_CACHE_CHECK([whether struct termios2 with TCGETS2/TCSETS2 is supported],
               [ac_cv_have_termios2],
               [AC_COMPILE_IFELSE([AC_LANG_PROGRAM([[
#include <asm/termbits.h>
#include <sys/ioctl.h>
]], [[
    struct termios2 t;
    (void) sizeof(t);
    (void) TCGETS2;
    (void) TCSETS2;
    return 0;
]])],
               [ac_cv_have_termios2=yes],
               [ac_cv_have_termios2=no])])
AS_IF([test "x$ac_cv_have_termios2" = "xyes"],
      [AC_DEFINE([HAVE_STRUCT_TERMIOS2], [1], [Define to 1 if ...])])
```

OHOS 上自动回退标准 termios 路径（tcgetattr/tcsetattr），行为等价——自定义波特率
（BOTHER）能力在 OHOS 本就不存在。此修改为 libc 特性探针（R8 例外，PR 中说明理由），
补丁不含 `__OHOS__` 平台宏，通过 PF5。

## 验证

- `./configure` rc=0，`config.h` 中 `HAVE_STRUCT_TERMIOS2` 为 `/* #undef */`
- `make -j1` rc=0
- `make check` PASS（unit-tests.sh 1/1）、proxy-tests.sh、random-test 全过
- conan create（ohos-aarch64 profile）G0-G4 全过，消费者测试通过

## 适用边界

- 适用：autotools 项目且上游用 `AC_CHECK_TYPES`/`AC_CHECK_DECLS` 检测 termios2；
  无上游 NO_TCGETS2 类开关的库（libmodbus 3.2.0 已交付实例）
- 同类风险：任何检测"类型"但实际使用"类型+宏常量"的 configure 检测
- 反例/边界：上游有编译期开关（如 bootterm NO_TCGETS2）→ 走
  `DRAFT-ohos-termbits-termios-fallback-knob` 的开关注入方案更优；
  若未来 OHOS kernel-uapi 头补齐 TCGETS2，应重评恢复自定义波特率

## 查重差异（七轴）

与 `DRAFT-ohos-termbits-termios-fallback-knob`：trigger_overlap=true（同命中
TCGETS2 undeclared）；solution_overlap=部分（同为回避 termios2 路径，机制不同：
开关注入 vs configure 检测修复）；combination_novelty/boundary_novelty=true
（configure 级组合检测为图谱内新方案，边界=无开关 autotools 库）。
与 E007（config.guess OHOS 补丁）、E102/E147/E148（__linux__ 排除）为 similar_to。
