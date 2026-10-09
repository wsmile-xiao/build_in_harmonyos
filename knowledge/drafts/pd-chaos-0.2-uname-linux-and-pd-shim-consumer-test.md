# Pd 老式 Makefile template 靠 `uname -s` 全串匹配选平台：本地 Linux 全绿，CI worker 才红；测 Pd 插件的 shim 里 `pd_new()` 只是分配原语

> Draft: `DRAFT-PD-CHAOS-020-UNAME-LINUX-PD-SHIM`
> Stem: `pd-chaos-0.2-uname-linux-and-pd-shim-consumer-test` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-PD-CHAOS-020-UNAME-LINUX-PD-SHIM
- **严重度**: 1
- **类别**: build-system|testing|ohos-platform
- **触发工具**: conan|clang|make|pd
- **阶段**: compilation|testing

## 错误特征

### 平台判定（本地完全复现不出来的那一类）

```
ld.lld: error: undefined symbol: main
ld.lld: error: undefined symbol: pd_new        # 以及 outlet_new / class_new / gensym ...
++++ info: linking objects in attract1.  for class attract1   # 扩展名是空的
```

`grep '^check' Makefile` 之类都不必看，关键特征是**产物文件名少了扩展名**、
链接行里没有 `-shared`。

### make 命令行覆盖只传了一半（第二次 make 回落宿主 cc）

```
cc  -rdynamic -shared -fPIC ... -o "latoomutalpha.pd_linux" "latoomutalpha.o" -lc libchaos.so
/usr/bin/ld: latoomutalpha.o: Relocations in generic ELF (EM: 183)
/usr/bin/ld: error adding symbols: file in wrong format
collect2: error: ld returned 1 exit status
```

### Pd 插件消费者测试的三个编译期/链接期坑

```
error: function cannot return function type 'int (t_method)'   # class_addbang 是宏
Segmentation fault (core dumped)                               # pd_new 里回调 c_new → 无限递归
0.360000014305  vs  期望 0.36                                   # t_float 是 32 位 float
```

## 根因

### 1. `UNAME := $(shell uname -s)` + `ifeq` 全串匹配，没有 OHOS 分支

pd-chaos 随包发布的是 Pd 官方老式 **Makefile template 1.0.11**：

```make
UNAME := $(shell uname -s)
ifeq ($(UNAME),Linux)
  EXTENSION = pd_linux
  ALL_CFLAGS += -fPIC
  ALL_LDFLAGS += -rdynamic -shared -fPIC -Wl,-rpath,"\$$ORIGIN",--enable-new-dtags
  SHARED_LDFLAGS += -Wl,-soname,$(SHARED_LIB) -shared
endif
```

分支条件是 `Linux` / `Darwin` / `ANDROID` / `MSYS` / `MINGW` / `GNU` / `Cygwin`。
**OHOS worker 的 `uname -s` 是 `HarmonyOS`**，一个都不命中 → `EXTENSION` 空、
`PD_PATH` 空、`-fPIC`/`-shared`/`-rdynamic`/`-Wl,-soname` 全丢。

**为什么本地看不出来**：WSL 开发机 `uname -s` 就是 `Linux`，自动走 Linux 分支。
这正是 W0b「历史命令/本地命令在 CI clean 环境里逐字可执行吗」要问的问题。
同族已在 `pd-libdir/1.11` 上踩过一次（那边是 pd-lib-builder 的 `system` 变量，
同样按 `uname` 全串匹配），两次的修法也一样：**命令行覆盖，不打补丁**
（命令行变量优先级高于 Makefile 里的 `:=` 赋值）。

顺带：`prefix` 是**字符串直拼**（`$(DESTDIR)$(objectsdir)`，中间无 `/`），
要给空值 `prefix=`，产物才落到包内 `lib/pd-externals/`；写 `prefix=/` 会得到
`<pkg>//lib/...`。

### 2. `make libdir_install` 在 `package()` 阶段会重链

`libdir_install: $(SOURCES:.c=.$(EXTENSION)) ...`——install 目标依赖全部插件，
make 判定过期就重链。`CC` 只在 `build()` 传过 → 这里回落 Makefile 默认的
`CC = cc`（宿主 gcc）→ 宿主 ld 不认 aarch64 → `Relocations in generic ELF (EM: 183)`。
修法：把 `CC=... UNAME=Linux prefix= STRIP=true` 收进 helper，**build() 与
package() 共用**。

### 3. `pd_new()` 是分配原语，不是「构造并调用」

插件构造函数第一行就是给自己拿结构体：

```c
void *logistic_new(t_symbol *s, int argc, t_atom *argv) {
    logistic_struct *logistic = (logistic_struct *) pd_new(logistic_class);
    ...
}
```

所以 Pd 的 `pd_new(cls)` 只做「按 `c_classsize` 分配 + 写 `ob_pd`」。shim 如果
在 `pd_new()` 里顺手回调 `cls->c_new`，就是
`pd_new → logistic_new → pd_new → …` **无限递归**，栈溢出 SIGSEGV。

排查时极具迷惑性：崩溃点看起来在第 28 个插件附近（stdout 块缓冲导致现场错位），
单跑那个插件却完全正常。正确分工：

- `pd_new(cls)` → 只分配；
- 测试自己实现 Pd 的 `newobject()` 等价物：`(*cls->c_new)(gensym(name), argc, argv)`。

### 4. 三个同源小坑

| 坑 | 现象 | 正解 |
|---|---|---|
| `class_addbang` 在 `m_pd.h` 里是自调用宏 | `error: function cannot return function type`（函数**定义**也被展开） | `#undef class_addbang` 后再提供同名符号 |
| `t_float` 是 32 位 float（`PD_FLOATTYPE`） | 期望 0.36 实得 0.360000014305 | 期望值同样过 `(t_float)` 收窄（32/64 位通用） |
| `struct _class` / `struct _outlet` 只有前置声明 | 不知道 sizeof / 字段 | 插件从不解引用它们，测试侧补够用的定义；`t_object`(`struct _text`) 有完整定义，`te_outlet` 偏移可信 |

另外 `gensym` 必须**驻留**：Pd 每个名字返回固定 `t_symbol`，插件先把
`gensym("reset")` 存进 class，之后还要 `gensym("float")`/`gensym("list")`，
复用槽位会覆盖已存的 selector。

## 影响范围

- 所有用 Pd 官方 Makefile template / pd-lib-builder 的外部对象集合
  （pd-chaos、pd-maxlib、pd-mjlib、pd-libdir 同族）。
- 更一般地：**任何靠 `uname -s` 全串匹配选平台分支的老式手写 Makefile**
  ——本地 Linux 永远绿，只有真机 worker 暴露。
- 所有「自带宿主运行时 shim 再 `dlopen` 插件」的插件类包测试
  （Pd 插件、编辑器插件、解释器扩展）。

## 推荐方案

**方法**: `read-makefile-uname-branch-and-force-it-on-command-line`

1. **拿到源码先判平台判定方式**：`grep -n 'UNAME\|uname -s\|ifeq ($(system)' Makefile`。
   全串匹配且没有目标 OS 分支 → make 命令行显式覆盖（`UNAME=Linux` / `system=Linux`），
   **不需要补丁**。
2. **覆盖收进 helper，build()/package() 共用**（install 目标会重链，二次回落宿主 cc
   是固定坑）。
3. **检查路径变量语义**：直拼型（`$(DESTDIR)$(objectsdir)`）要给空 `prefix=`；
   拼路径型要给 `/lib`。
4. **Pd 插件测试**：
   - `readelf --dyn-syms <x>.pd_linux | awk '$7=="UND"'` 对全部插件取并集，
     shim 只实现真正 import 的符号（本例 14 个，**含 `s_float`/`s_list` 两个数据符号**）；
   - 消费者用 `-rdynamic` 编译，`dlopen(RTLD_NOW | RTLD_LOCAL)`，
     **不要 `dlclose`**（注册进去的方法指针指向插件代码）；
   - `pd_new()` 只分配，对象创建走 `(*c_new)(sym, argc, argv)`；
   - `#undef class_addbang`；`gensym` 驻留；期望值过 `(t_float)`。
5. **Pd 头文件的来源**：`puredata` 是 application 包、`cpp_info.includedirs` 为空，
   按依赖 `package_folder` 探测 `m_pd.h`；**不要**去改被依赖包的配方（W2/JC6 单包）。

## 验证命令

```bash
# 1) 不覆盖 UNAME（模拟 HarmonyOS）——本地 Linux 上也这样复现
make -n UNAME=HarmonyOS | head -20          # 看不到 -shared / EXTENSION 为空

# 2) 正确覆盖
make -j1 CC="<OHOS clang>" PD_INCLUDE="<puredata pkg>/include/pd" \
     UNAME=Linux prefix= STRIP=true
ls *.pd_linux | wc -l                        # 28

# 3) 插件的运行期形状
readelf -d <class>.pd_linux | grep -E 'RUNPATH|NEEDED'
# 期望 RUNPATH [$ORIGIN]，NEEDED 只有 libc.so + 辅助库
readelf --dyn-syms -W <class>.pd_linux | awk '$7=="UND"{print $8}' | sort -u
```

## 取证记录

- 包: pd-chaos 0.2（`archives/p/pd-chaos/0.2`）
- 环境: OHOS aarch64，clang 15，profile `ohos-aarch64-wsl`
- 逐字证据: `archives/p/pd-chaos/0.2/notes.md`（第 3 节三个构建坑 + 第 5 节 shim 五个语义坑）
- 交叉验证: 同族 `pd-libdir/1.11` notes.md 3.1（`system=Linux` 同一坑的另一个变体）