# readline 8.3 把老式 typedef「Function」收进 WANT_OBSOLETE_TYPEDEFS 守卫：hook 赋值必须用公开的 rl_hook_func_t

> Draft: DRAFT-pal-0.4.3-readline-private-function-typedef-not-exported
> Stem: `pal-0.4.3-readline-private-function-typedef-not-exported` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-pal-0.4.3-readline-private-function-typedef-not-exported
- **严重度**: 3
- **类别**: compat | headers | api | third-party-library
- **触发工具**: clang（`conan create` 的 `build()` 阶段）
- **阶段**: compilation
- **来源包**: pal 0.4.3（本条目面向**一切沿用老式 readline typedef/宏的上游 C 包**）

## 错误特征

报错停在**使用点**，不是定义点，而且那个标识符短得像个类型名：

```
manage.c:406:26: error: use of undeclared identifier 'Function'
    rl_pre_input_hook = (Function*) pal_rl_ncurses_hack;
                         ^
```

一手出处：`explore/make.log:157`（首轮），`explore-build2.log:70`（复现）。
链接期、平台运行期都没有任何提示 —— 它**不是**能力墙，也不是缺依赖。

## 根因分析

`Function / VFunction / CPFunction / CPPFunction` 是 readline 早期的函数指针 typedef，
**从来不是它对外承诺的稳定 API**。本仓依赖树固定用 conan `readline/8.3`，其安装出来的公开头
`readline/rltypedefs.h` 把这一族老式名字收进了 **opt-in 宏守卫**里并标了 deprecated（行号取自本包实际安装的那份头）：

| 位置 | 原文 | 含义 |
|---|---|---|
| `rltypedefs.h:29` | `Old-style, attempt to mark as deprecated in some way people will notice.` | 库方自己的注释，已声明不稳定 |
| `rltypedefs.h:31` | `#if !defined (_FUNCTION_DEF) && defined (WANT_OBSOLETE_TYPEDEFS)` | **守卫需要 WANT_OBSOLETE_TYPEDEFS** |
| `rltypedefs.h:34` | `typedef int Function () __attribute__((deprecated));` | 老名字在守卫**之内** |
| `rltypedefs.h:39` | `#endif /* _FUNCTION_DEF && WANT_OBSOLETE_TYPEDEFS */` | 守卫结束 |
| `rltypedefs.h:64` | `typedef int rl_hook_func_t (void);` | 「New style.」段里的**公开**替代类型 |
| `rltypedefs.h:76` | `#define rl_ivoidfunc_t rl_hook_func_t` | 公开族内部的别名 |
| `readline.h:608` | `extern rl_hook_func_t *rl_pre_input_hook;` | 该变量**本来就按公开类型声明** |

而 `WANT_OBSOLETE_TYPEDEFS` 在整个安装出来的包里**没有任何地方定义**
（`grep -rl WANT_OBSOLETE_TYPEDEFS <CONAN_HOME>/p` 只命中 `rltypedefs.h` 自身）。
⇒ `Function` 对下游**事实上不可见**，`manage.c` 那行强转就成了未声明标识符。

关键判断：**强转本来就是多余的**。`readline.h:608` 声明的目标类型就是 `rl_hook_func_t *`，
把右值强转成 `Function*` 只是把一个私有名字写进了类型位置。

⇒ **这与目标平台无关**：同一份依赖树在 Linux/macOS + clang/gcc 上同样失败。
⛔ 不要把它写成"OHOS/鸿蒙不兼容"、⛔ 不要写成"缺工具链"或"缺依赖"。

## 本包的实测形状：一处孤点，其余早已是公开类型

`pal 0.4.3` 上游源码里 hook 赋值共 6 处，**5 处早已写公开类型**，只有 `manage.c` 是孤例：

| 文件:行 | 原文 | 状态 |
|---|---|---|
| `src/manage.c:406` | `rl_pre_input_hook = (Function*) pal_rl_ncurses_hack;` | **出错点，唯一** |
| `src/rl.c:137` | `rl_pre_input_hook = (rl_hook_func_t*) pal_rl_default_text_fn;` | 已是公开类型 |
| `src/remind.c:96`、`:105` | 同上形态 | 已是公开类型 |
| `src/add.c:97`、`:264` | 同上形态 | 已是公开类型 |

⇒ 修法与同包既有写法**完全一致**，等于替上游把它自己剩下的那一处补齐；这不是"为鸿蒙改 API"。
补丁固化为单行 hunk：`archives/p/pal/0.4.3/patches/0002-manage.c-readline-public-hook-type.patch`
（`patch_type: portability`），改后 `rl_pre_input_hook = (rl_hook_func_t *) pal_rl_ncurses_hack;`。

改后读数：`explore-smoke.log:10` 记 `MAKE_RC=0`；本包 `conan create` 与 W3 本地 CI 通过
（判决件在 `archives/p/pal/0.4.3/reports/`）。

## 处方（`rec_approach: use-public-readline-hook-typedef`）

**只改类型名，不改回调实现、不改注册时序**：把老式/私有 typedef 换成同族公开类型 `rl_hook_func_t`
（`rl_event_hook` 同一条），以 portability 补丁落在出错行。

两条被实测否决的替代路（记下来免得重复试错）：

1. **编译期把老名字唤回**（`-DWANT_OBSOLETE_TYPEDEFS` 或直接 `-DFunction=...`）：等于替上游继续依赖一个
   带 `deprecated` 标记、库方已声明不保证稳定的名字；签名与解法都不可复用，还会把"同类包在别处撞同一条"
   的事实抹掉。⛔ 不要用。
2. **包内 vendor 一份去掉守卫的老式头**：本仓 `archives/b/bcal/2.5/res/headers/readline/` 与
   `archives/b/bitwise/0.50/res/headers/readline/` 就是把 `:31` 的守卫写成 `#if !defined (_FUNCTION_DEF)`
   （去掉 WANT_OBSOLETE_TYPEDEFS 条件）从而无条件再导出 `Function`。那是那两包自己的路数，会把 ABI 与版本
   一致性风险引进构建 —— ⛔ **不要拿它们当本条目的先例**。

## 命中特征与预扫

```
prescan_pattern: \(Function\s*\*\s*\)|rl_pre_input_hook\s*=|rl_event_hook\s*=|VFunction|CPFunction
prescan_globs:   **/*.c,**/*.h
```

三步定性（缺一步就不要下结论）：

1. 在**依赖实际安装出来的那份公开头**里查这个名字是否被条件编译守卫罩住、守卫要哪个宏；
2. 查该宏在整个缓存里有没有人定义（`grep -rl`，⛔ 只看头文件自己）；
3. 查同一头文件的「New style.」段有没有公开替代类型，并和目标变量的 `extern` 声明对齐。

## 适用边界与解除条件

**适用**：编译期符号未声明，且该符号属第三方库的老式/私有 typedef 或宏（典型是 `(Function*)` 这类强转、
或按老式 readline 接口给 `rl_pre_input_hook`/`rl_event_hook` 赋值）。同族老式宏（`USE_PROMPT_INVIS` 一类）
常与这批私有名同时代出现，但**pal 0.4.3 源码内该宏 0 命中**（实测 grep 无结果）⇒ 不要据此断言本包用到它。

**不适用 / ⛔ 混引即错**：libc、OpenSSL、gnulib 侧的系统符号消失。本仓 `knowledge/graph/index.tsv` 里
`undeclared identifier` 同形状的正式条目 `E062`(:288)、`E115`(:341)、`E127`(:353)、`E152`(:378)、
`E162`(:388)、`E171`(:397)、`E211`(:437) 的失效面全在那一侧，**没有一条覆盖"第三方库头里的老式/私有 typedef
被收进 opt-in 守卫而不再导出"这一层**。其中 `E127` 的 `rec_approach` 是 `undef-macro`（`graph/E127.kv:24`，
配 `:26` 的宏守卫与 `:28` 的 source-edit），走的是"补/删宏"路线，与本条"换公开类型"**不同解** ⇒
引它会把读者推向本文已被否决的宏垫片。最近邻但不同机理：`DRAFT-tau-1.0.0-muon-assertion-macro-message-argument.kv:12`
的 `expected expression` 出自 `__VA_ARGS__` 空展开 —— 符号本身存在、失效层次在宏展开期；本条是类型名压根不在可见集合里。

**解除条件**：上游自行改用公开类型，或依赖树换成确实无条件导出该名字的 readline 版本。

## 取证命令（可直接复制）

```sh
RL=$(find "$CONAN_HOME/p" -path "*/include/readline/rltypedefs.h" | head -1)
grep -nE "WANT_OBSOLETE_TYPEDEFS|typedef int Function|rl_hook_func_t" "$RL"
grep -rl "WANT_OBSOLETE_TYPEDEFS" "$CONAN_HOME/p" | grep -v "rltypedefs.h"
# 守卫之外无人定义该宏 => 命中本条
```
