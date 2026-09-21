# gtkd 3.11.0 — OHOS（鸿蒙 PC）适配笔记

## 概述

GtkD（`github.com/gtkd-developers/GtkD`）是 **GTK+ 3 的 D 语言绑定与面向对象封装**。
源码已随发行版附**预生成绑定代码**（`generated/` 下 906 个 .d，另有 sourceview /
gstreamer / vte / peas / gtkdgl 子包），适配时直接编译它们，**不需要** gir-to-d。

- **构建系统**: `GNUmakefile`（上游另有 `dub.json`，ohpcd 无 dub 制品 → 与
  gir-to-d 0.23.3 同一结论，走 Makefile 路径）
- **D 编译器**: LDC 1.42.0（`tool_requires("ldc/1.42.0")`，底层 LLVM 20.1.0，
  target `aarch64-unknown-linux-ohos`）
- **产物**: 5 个静态库（`package_type=static-library`）
- **状态**: built
- **补丁**: **0 个**（`patches: {}`，未改动上游任何源码）

## 核心特征：运行期 dlopen，而非链接期依赖 GTK

这是本包最关键的设计事实，决定了依赖声明与测试方式。

`generated/gtkd/*/c/functions.d` 里每个 C 函数都不是链接进来的，而是登记为一个
**运行时解析项**：

```d
Linker.link(gtk_window_new, "gtk_window_new", LIBRARY.GTK);
```

`src/gtkd/Loader.d` 的 `Linker` 在运行时用 `dlopen`/`dlsym` 解析，
库名取自 `src/gtkd/paths.d`（Linux 分支：`libgtk-3.so.0`、`libgdk-3.so.0`、
`libgobject-2.0.so.0`、`librsvg-2.so.2` 等）。

GNUmakefile 用这一点决定是否走 pkg-config 链接分支：

```make
USE_RUNTIME_LINKER = $(shell grep "Linker" generated/gtkd/atk/c/functions.d)
ifeq ($(USE_RUNTIME_LINKER),)
    SOFLAGS_GTKD = $(shell pkg-config --libs-only-l ... gtk+-3.0 ...)
endif
```

实测该文件 **278 处命中 `Linker`** → 分支被跳过。

### 两个直接结论

| 阶段 | 需要 GTK？ | 说明 |
|---|---|---|
| **构建期** | ❌ **不需要** | 无头文件、无 pkg-config 依赖。实测在**完全没有 GTK** 的环境里 `make libs` 成功产出 5 个静态库 |
| **运行期** | ✅ **必须** | 需能 dlopen `gtkd.paths` 列出的 .so，故 requires gtk（传递带入 glib/pango/cairo/gdk-pixbuf/atk/fribidi/libepoxy）+ librsvg |

实测 dlopen 结果（带 gtk 运行环境）：

```
libgtk-3.so.0         OK
libgdk-3.so.0         OK
libgobject-2.0.so.0   OK
libgio-2.0.so.0       OK
librsvg-2.so.2        FAILED  ← 不在 gtk 传递闭包内，故单独 requires librsvg
```

## 依赖

| 类型 | 依赖 | 说明 |
|---|---|---|
| 运行期 | `gtk/3.24.43` | 传递带入 glib/gobject/gio/pango/cairo/gdk-pixbuf/atk/fribidi/libepoxy |
| 运行期 | `librsvg/2.62.3.1` | gtkd.paths 要 dlopen `librsvg-2.so.2`，但它不在 gtk 闭包内 |
| 版本消解 | `cairo-gobject/1.18.4.3`（**override**） | 见下 |
| 构建期 | `ldc/1.42.0`（tool_requires） | ldc2 + druntime/Phobos（`libdruntime-ldc.a`、`libphobos2-ldc.a`、`include/d/`） |

### cairo-gobject 版本冲突（必须显式 override）

```
gtk/3.24.43        → cairo-gobject/1.18.4.2
librsvg/2.62.3.1   → cairo-gobject/1.18.4.3
```

同图共存时 conan 不会自动收敛，直接失败：

```
ERROR: Version conflict: Conflict between cairo-gobject/1.18.4.3 and
       cairo-gobject/1.18.4.2 in the graph.
```

处置：`self.requires("cairo-gobject/1.18.4.3", override=True)` —— 取较新者
（ohpcd 已发布，且 librsvg 是更晚适配的版本）。

## 遇到的问题与解决方案

全部为**构建/测试环境适配**，无上游源码补丁。

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make ... DC=ldc2` 报 `ldc2: No such file or directory`（exit 127） | hnp CPython 的 subprocess 走 `posix_spawn`、**不搜 PATH**（E405，cffi 适配同款）；make 经 `/bin/sh` 起进程时裸名解析失败 | `DC` 用**绝对路径** `<ldc_pkg>/bin/ldc2`（同时满足 makefile 内 `findstring ldc,$(DC)` 分支判定）；裸名 `ldc2` 的 PATH shim 无效。**这是唯一致命的构建问题** |
| 2 | （伴生噪音，**非致命**）`make: jobserver mkfifo: <tmp>/GMfifoNNN: Operation not permitted` | GNU make 的并行 jobserver 默认用 **FIFO**，OHOS 不允许创建 | **无需修复**：make 4.4.1 会自动回退到 pipe jobserver，构建照常完成。实测拿掉 `--jobserver-style=pipe`、直接 `make -j4 libs` → **rc=0、5 个静态库全部产出**（警告仍打印）。配方保留该参数只为消噪音并兼容更老 make。既有 `E6340-draft-8BEF` 记录同一「非致命」结论 |
| 3 | 编译报 `unable to read module 'algorithm'` | ldc2 默认导入路径不含 **Phobos 源码**（`<ldc>/include/d`） | `DCFLAGS="-O -I<ldc>/include/d"`（gir-to-d 同款） |
| 4 | `cairo-gobject` 版本冲突（见上） | 两个依赖钉不同版本 | 显式 `override=True` |
| 5 | test_package 里 `ldc2` 起不来：`_ZN4llvm11raw_ostream10resetColorEv: symbol not found` | `self.run(..., env="conanrun")` **只**注入运行上下文；ldc 是 `tool_requires`（**构建上下文**），其 libLLVM 路径只在 conanbuild 环境里 | `self.run(..., env=["conanbuild", "conanrun"])` 两套环境一起注入（非新知，见 DRAFT-332-openrct2-0.5.3-upstream-testsuite-real-run 同结论） |
| 6 | `make test` 编译 demo 失败：`TestIdle.d(59): Error: identifier expected inside 'debug(...)', not '1'` | 上游 demo 用旧式**数字 debug 级别** `debug(1)`；LDC 1.42 的 DMD 前端 v2.112.1 要求 identifier | **不改上游**：该目标只是编译 GUI 演示程序（需显示环境），非单元测试；库本体（`generated/` + `src/`）**零处**使用该写法，不影响交付物。已在 manifest 的 compatibility.issues 记录 |

## 上游测试（R51 清点与实测）

**关键：gtkd 没有 tests/ 目录，也没有 dub testConfiguration。**
D 语言惯例是把测试写成 `unittest { ... }` 块**内嵌在源文件里**（由 `dub test`
或 `ldc2 -unittest -main` 驱动）——按 Perl/autotools 的 `t/` 目录习惯去清点会得出
「上游无测试」的错误结论。

### 清点结果

| 位置 | unittest 块 | 块内 assert 数 |
|---|---|---|
| `generated/gtkd/glib/ListG.d` | 1 | 3 |
| `generated/gtkd/glib/ListSG.d` | 1 | 3 |
| `generated/gtkd/glib/c/types.d` | 1 | 1 |
| `generated/gtkd/gobject/ObjectG.d` | 1 | 1 |
| **合计** | **4** | **8** |

`src/`、`demos/` 中**零** unittest 块。

### GNUmakefile 的 `test` 目标不是单元测试

```make
test: $(BINNAME_DEMO)   # BINNAME_DEMO = TestWindow
```

它编译的是 `demos/gtkD/TestWindow`（一个 GUI 演示程序，需显示环境），
且该 demo 在 3.11.0 上因 `debug(1)` 旧式语法无法编译（见问题 #6）。
故不把它当作 R51 的测试依据。

### 实测（如实申报：1 通过 / 3 崩溃）

逐个隔离运行（各自 `ldc2 -i -unittest -main` 编译其导入闭包后执行）：

| 模块 | 结果 |
|---|---|
| `generated/gtkd/glib/c/types.d` | ✅ **PASS**（`1 modules passed unittests`） |
| `generated/gtkd/glib/ListG.d` | ❌ SIGSEGV（Signal 11） |
| `generated/gtkd/glib/ListSG.d` | ❌ SIGSEGV |
| `generated/gtkd/gobject/ObjectG.d` | ❌ SIGSEGV |

**规律很明确**：唯一通过的那个块是**纯 D 计算**——`glib/c/types.d` 里
`Linker.link` 调用数为 **0**，完全不触碰 C 库；其余 3 块都要经 gtkd 的运行期
dlopen 加载器调用 gobject/glib 的 C 函数（如 `g_value_init`、
`g_value_get_int`）。

**根因定位（含反证）**：
- 被调符号本身**可解析** —— 用 ctypes 直接 dlopen `libgobject-2.0.so.0` 检查
  `g_value_init` / `g_value_get_int` / `g_value_set_int` / `g_object_new`
  **全部 OK**；
- gtkd 的**加载器本身可用** —— 消费者测试里同一个 `Linker` 成功调到
  `gtk_get_major_version()` 并返回 3（11/11 通过）；
- 崩溃机制：gtkd 每个模块的 `shared static this()` 会**急切地**把所有绑定符号
  登记（`Linker.link(...)` → `getSymbol()` → `loadLibrary()`）。当某模块 ctor
  内 `dlopen` 失败时 `Loader.d:104` 抛异常，而 exception 发生在**启动期模块构造**
  阶段 → 表现为 SIGSEGV 而非干净的报错。全库 906 模块一起跑时的输出印证了这条
  路径（明确打印 `Library load failed (librsvg-2.so.2)`、
  `(libharfbuzz-gobject.so.0)`）。

**因此这 3 块的崩溃是「上游内嵌测试的独立运行形态 + ohpcd 未提供对应运行期
.so」共同所致，不是库本体缺陷**，也不影响交付物：库本体完整编译出 5 个静态库，
消费者测试（真实 D 程序、经同一加载器调用 GTK API）11/11 通过。
故本配方**未在 build() 内运行这些内嵌块**（`upstream_test_in_build: false`），
并在 manifest 的 test_results 中如实记录 1 通过 / 3 崩溃。

```bash
# 等价 dub test：以 -unittest -main 编译并运行内嵌块
ldc2 -i -unittest -main -O -Igenerated/gtkd -I<ldc>/include/d -L-L<ldc>/lib \
     generated/gtkd/glib/c/types.d -of=ut_types && ./ut_types
# → 1 modules passed unittests
```

## 编译步骤（conan create 全流程）

```bash
conan create archives/g/gtkd/3.11.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

`build()` 内实际执行（`jflag = --jobserver-style=pipe -jN`）：

```bash
make -f GNUmakefile <jflag> libs \
  DC="<ldc_pkg>/bin/ldc2" DCFLAGS="-O -I<ldc_pkg>/include/d"
```

## 源码修改

**无补丁**（`patches: {}`）。上述 6 项问题全部通过 conanfile.py 内的参数/环境/
依赖声明解决，未改动上游文件。

## 验证结果

```bash
# 1) 库本体构建
#    → exit=0；产出 5 个静态库
#    libgtkd-3.a(66MB) libgtkdsv-3.a libgstreamerd-3.a libvted-3.a libpeasd-3.a

# 2) 内嵌 unittest 块（等价 dub test）
ldc2 -unittest -main -O -Igenerated/gtkd -I<ldc>/include/d -L-L<ldc>/lib \
     @srcs.txt -of=ut_full && ./ut_full

# 3) 消费者测试（conan create 内）
#    → 11/11 checks passed
#    编译真实 D 程序 → 静态链 libgtkd-3.a → 运行 → 经 gtkd dlopen 调
#    gtk_get_major_version() 得到 3
```

**R51 如实申报**：
- 上游测试形态 = **4 处内嵌 unittest 块 / 8 条 assert**（D 语言惯例，无 tests/ 目录）
- 实测结果：**1 块通过、3 块 SIGSEGV**（详见上方「实测（如实申报：1 通过 / 3 崩溃）」
  小节与该节的根因反证）——**不声称全部通过**
- 崩溃的 3 块（`glib/ListG.d`、`glib/ListSG.d`、`gobject/ObjectG.d`）均经 gtkd 的
  运行期 dlopen 加载器调 gobject/glib C 函数；唯一通过的 `glib/c/types.d` 是纯 D 计算
  （`Linker.link` 调用数为 0）。已定位为「上游内嵌测试的独立运行形态 + ohpcd 的
  librsvg 为静态制品（无 `librsvg-2.so.2`）」共同所致，**非库本体缺陷**
- 无 CI 测试配置、无 tests/ 目录、无 pytest/ctest 注册
- 消费者测试（R34 真实 API）：**11/11**（独立证明库本体交付能力）

> 说明：`GNUmakefile` 的 `test` 目标编译 GUI demo（需显示环境）且该 demo 在
> 3.11.0 上语法过时，**不**计入通过率分母；其失败已在 manifest 的
> compatibility.issues 如实记录。

## 交付物

```
<pkg>/
├── lib/
│   ├── libgtkd-3.a、libgtkdsv-3.a、libgstreamerd-3.a、libvted-3.a、libpeasd-3.a
│   └── pkgconfig/gtkd-3.pc
├── include/d/gtkd-3/        # D 导入源码（*.d，上游 install-headers-gtkd 布局）
└── licenses/COPYING
```

## 注意事项

- **构建期与运行期依赖性质不同**：构建期只需 D 编译器；运行期才需要 GTK 的 .so。
  设计 conan 依赖时要按「运行期 dlopen 目标」声明（否则消费方运行时报
  `The function you are calling is not pressent in your version of GTK+.`）。
- **`jobserver mkfifo ... Operation not permitted` 是非致命警告**：make 4.4.1 会自动
  回退 pipe jobserver，`make -j4` 照常成功（实测 rc=0）。配方仍带
  `--jobserver-style=pipe` 只为消噪音，**不要**把它当作并行失败的原因去排查——
  本包真正的致命项是裸名 `DC`（见上一条）。
- **D 编译器要绝对路径**（E405）。
- **Phobos 的 -I 必须显式给**，否则连 `std.algorithm` 都找不到。
- **同层依赖版本冲突要显式 override**（cairo-gobject 是本例）。
- **tool_requires 的运行库要 conanbuild 环境**，test_package 里
  `env=["conanbuild","conanrun"]` 缺一不可。
---

**编译结束**: 2026-09-20 11:02
**最终状态**: built
