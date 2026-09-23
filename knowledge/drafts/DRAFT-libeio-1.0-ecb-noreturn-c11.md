# DRAFT-libeio-1.0-ecb-noreturn-c11

## 问题 (Problem)

libeio 1.0（scunningham/libeio master）在 HarmonyOS PC (aarch64) 上编译时，
clang 15（OHOS SDK 26.0.0.18，默认 C11 模式）报：

```
./ecb.h:475:42: error: '_Noreturn' keyword must precede function declarator
  ecb_inline void ecb_unreachable (void) ecb_noreturn;
```

## 根因 (Root Cause)

libeio 自带 2012 版 `ecb.h`：

```c
#if ECB_C11
  #define ecb_noreturn   _Noreturn
#else
  #define ecb_noreturn   ecb_attribute ((__noreturn__))
#endif
```

`ECB_C11` 由 `__STDC_VERSION__ >= 201112L` 判定，clang 15 默认满足；于是
`ecb_noreturn` 展开为 C11 标准关键字 `_Noreturn`。但 ecb 的所有使用点都是
"尾部放置" 风格（`ecb_inline void f (void) ecb_noreturn;`）——`_Noreturn`
在 C11 语法中必须位于函数声明最前（declarator 之前），旧 GCC 宽松容忍尾部，
clang 15 严格按标准报错，编译即中断。

## 方案 (Solution)

不改动各使用点声明顺序，仅统一宏定义——两个分支都改为
`ecb_attribute ((__noreturn__))`（即 `__attribute__((noreturn))`）：

```c
#if ECB_C11
  #define ecb_noreturn   ecb_attribute ((__noreturn__))
#else
  #define ecb_noreturn   ecb_attribute ((__noreturn__))
#endif
```

GCC/Clang 扩展属性允许置于声明尾部，语义与 `_Noreturn` 等价；一处宏改动
修复全部使用点，无平台宏、无使用点改动（R8 合规），补丁文件：
`archives/l/libeio/1.0/patches/0001-ecb.h.patch`。

## 验证 (Validation)

- 改前：`clang -O2 -I. -c eio.c` → `ecb.h:475 error: '_Noreturn' keyword must precede function declarator`
- 改后：`make -j1` 全量通过（仅上游格式 warning）
- `conan create` + `conan-verify`：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS
- 消费者用例（test_package，eio_init/eio_nop/eio_poll）与鸿蒙专项测试
  `tests/ohos_test.c`（eio_busy/eio_readdir/eio_stat/eio_unlink/eio_rmdir）
  实跑 rc=0

## 适用边界 (Boundary)

- 适用于内嵌旧版 ecb.h（<2015 快照）且以 C11 模式编译的库：libeio、
  libev 早期 vendored 副本等。
- 非 C11 路径不受影响（原分支本就是 `__attribute__((__noreturn__))`）。
- 若上游 ecb 已升级为 noreturn 前置写法，无需本补丁；不得对现代 ecb.h
  无条件套用。

## 查重 (Dedup)

- 图谱 `knowledge/graph/index.tsv`：无 noreturn/ecb_noreturn/_Noreturn 条目
- 正式文档 `knowledge/doc/`：无独立条目（musl-glibc 对比文档顺带提及，非条目）
- 草稿 `knowledge/drafts/`：无同 stem 草稿
- 与 E041/E071（automake 版本不匹配）、E007/E122/E160（config.guess/sub
  OHOS 识别）、E116（automake perl 模块）均无交集
- 判定：未命中，新增草稿 DRAFT-libeio-1.0-ecb-noreturn-c11
