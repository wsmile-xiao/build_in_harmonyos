# pcc-libs

`pcc-libs` 是 **Portable C Compiler (pcc)** 的运行时库源码，包含：

| 组件 | 产物 | 用途 |
|------|------|------|
| `libpcc` | `libpcc.a` | 核心运行时：64 位整数例程、符号提取、复数 long double 乘除 |
| `libsoftfloat` | `libpccsoftfloat.a` | 软件浮点：单/双精度 IEEE 运算与比较 |
| `csu` | `crtbegin*.o` `crtend*.o` | C 启动代码（构造/析构表） |
| `libF77` / `libI77` | （非默认目标） | Fortran 77 运行时 |

上游：https://github.com/PortableCC/pcc-libs （pcc 官方维护者仓库，
commit `5fd7d9e34419`，对应任务快照 1.2.0-devel-20211015）
许可证：BSD-3-Clause

## 与 pcc 的关系

`pcc` 是编译器，`pcc-libs` 是编译器产出的代码所链接的运行时支持。两者是独立的
Conan 包、独立任务、独立 PR。`pcc-libs` **不依赖** `pcc` 即可构建——它的
`configure.ac` 用 `AC_CHECK_TOOLS([CC], [pcc gcc cc])` 自动挑选编译器。

## 版本

| 版本 | 状态 | Conan 引用 |
|------|------|-----------|
| 1.2.0-devel-20211015 | built | `pcc-libs/1.2.0-devel-20211015` |

## HarmonyOS PC 适配要点

1. **平台白名单**：上游 `configure.ac` 与预生成的 `configure` 都只认固定几个目标 OS。
   OHOS 需要新增 `linux-ohos*` 分支；注意 `config.sub` 会把三元组规范化成
   `aarch64-unknown-linux-ohos`，且 shell 的 `case` 是前缀匹配，`linux*)` 会吞掉
   `linux-ohos`，因此分支名必须是 `linux-ohos*` 且写在前面。
2. **config.guess / config.sub**：2021 年版不识别 HarmonyOS，且 config.guess
   的分支是 `echo`/`exit` 风格（末尾没有 `echo $GUESS`）。
3. **long double**：AArch64 上是 IEEE binary128，上游 `cxmuldiv.c` 只实现了 x87
   与 128 位大端布局。
4. **`__FLOAT_WORD_ORDER__`**：clang 不定义该宏，上游字节序判断会静默退化，
   导致 `__signbitl` 读错位并使复数例程崩溃。
5. **softfloat 双字序**：上游 `libsoftfloat/arch/aarch64/aarch64-gcc.h` 用 32 位
   ARM 宏 `__VFP_FP__`/`__ARMEB__` 判断 FPA 字交换，aarch64 编译器都不定义，
   误入交换分支导致所有双精度算术返回垃圾；AArch64 必须恒取自然序。
6. **csu 启动代码**：复用 `linux/` 会因 `__x86_64__` 未定义而生成 32 位表项，
   且上游对 ctor 用指针宽度、对 dtor 用 `__x86_64__` 判据不一致，需统一。

详细过程见 `1.2.0-devel-20211015/notes.md`。

## 安装布局

```
<prefix>/lib/pcc/aarch64-unknown-linux-ohos/1.2.0.DEVEL/
├── include/   float.h limits.h stdarg.h stdbool.h stddef.h iso646.h ...
└── lib/       libpcc.a libpccsoftfloat.a crtbegin*.o crtend*.o
```

该路径由 pcc 驱动按目标三元组查找运行时，属于上游约定，未作改动。
配方通过 `PCC_LIBS_ROOT` 环境变量对外暴露该目录。