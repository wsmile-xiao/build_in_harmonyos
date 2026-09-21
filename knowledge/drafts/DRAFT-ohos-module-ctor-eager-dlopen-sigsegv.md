# DRAFT-ohos-module-ctor-eager-dlopen-sigsegv — 运行期 dlopen 型绑定的「启动期急切登记」会把「缺一个 .so」放大成 SIGSEGV

> Contributor: 3211 / Status: **DRAFT** / Updated: 2026-09-20 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-module-ctor-eager-dlopen-sigsegv`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E004` musl BIND_NOW，扩展 NEEDED 无 libpython → ImportError | 已收录 | **加载期**符号解析失败，且是**可读的 ImportError**，修法是改 LDSHARED 加 `-lpython` | 本条是**启动期模块构造阶段**的失败，且**错误信息被销毁**（只有 SIGSEGV）。修法也不同：E004 补链接标志，本条补**运行期依赖 .so** 或探针申报。两者都属「符号/库缺失」，但一个能报错、一个不能报错——**能否报错**正是本条要解决的核心困难 |
| `E024` Unix domain socket 受限 | 已收录 | AF_UNIX `bind()` 被 SELinux 拒绝（EPERM，**可读错误**） | 同为「平台能力限制」，但 E024 的错误是干净的 `PermissionError`，本条的错误是 SIGSEGV。本条的方法论增量在于：**在错误信息不可读时如何取证并区分「环境缺件」与「平台不支持」**（探针 + 隔离运行 + ctypes 反证），该方法论可迁移到任何 SIGSEGV 类现场 |
| `opencsg-1.8.2-dt-needed-verification-for-runtime-dlopen-libs` | 草稿 | 从**产物验证**侧：「运行期 dlopen 型库不应把依赖硬链进 DT_NEEDED」 | 那条在**构建完成之后**查 DT_NEEDED；本条在**运行测试时**处理「dlopen 目标在环境里缺失」的崩溃表现与取证。二者是同一条链的两端（一个管不该链、一个管链不到/找不到） |
| `DRAFT-libcec-8.1.7-cmake-system-name-linux-soname` | 草稿 | 运行期 dlopen 目标的 soname 命名/查找问题 | 那条解决「名字对不对」（soname 匹配）；本条解决「名字对但目标不存在时，进程为什么以 SIGSEGV 表现，以及如何证明是这个原因」 |
| `DRAFT-test-discovery-per-language-convention` | 草稿 | 按语言生态惯例发现上游测试（D 的 unittest 在源码内嵌） | 那条管**找到**测试；本条管**跑测试时崩溃如何判读**。gtkd 适配中二者先后命中（先按 D 惯例找到 4 个内嵌块，再面对其中 3 个 SIGSEGV） |

**全库查证**：对 `启动期模块/构造`、`shared static this`、`模块初始化.*崩`、`构造阶段.*异常` 四组关键词在 `knowledge/drafts/*.kv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md` 中检索，**命中 0 条**（`DRAFT-chaiscript-6.1.0-constructor-stdlib-vs-dynload` 讲的是 C++ 构造函数选型导致 load_module 失败即 abort，属「构造函数选错」而非「启动期批量登记 + 缺件」；且其失败是 Signal 6 abort 带长提示，本条是静默 SIGSEGV）。

## Scope（何时用）

满足以下**任一**信号即命中：

| 信号 | 检查命令 |
|---|---|
| 测试/程序以 `Signal 11` / `SIGSEGV` / `core dumped` 结束，且无可用错误信息 | 直接观察运行输出 |
| 库采用「运行期 dlopen 延迟绑定」 | `grep -rn "loadLibrary\|dlopen\|dlsym" <src>` |
| 存在**启动期**批量登记的构造器 | `grep -rn "shared static this\|static this()" <src>`（D）；C++ 为全局对象 ctor / `__attribute__((constructor))` |
| 崩溃前 stderr 出现过 `Library load failed (...)` / `Error loading shared library ...` | 捕获**完整 stderr**（不要只看测试汇总行） |
| 同一套件中**纯计算**的用例通过、凡触碰 C 库的用例全崩 | 隔离运行比对 |

**实测案例：gtkd 3.11.0**（OHOS aarch64 + LDC 1.42.0）

`generated/gtkd/*/c/functions.d` 里每个 C 函数登记为：

```d
Linker.link(gtk_window_new, "gtk_window_new", LIBRARY.GTK);
```

由 `src/gtkd/Loader.d` 在运行时 `dlopen`/`dlsym` 解析，库名取自 `gtkd.paths`。
每个模块的 `shared static this()` 在**启动期**急切登记该模块全部符号。

## Symptom（真实表现）

上游 4 个内嵌 unittest 块逐个隔离运行的结果：

| 模块 | `Linker.link` 调用数 | 结果 |
|---|---|---|
| `generated/gtkd/glib/c/types.d` | **0**（纯 D 计算） | ✅ 通过（`1 modules passed unittests`） |
| `generated/gtkd/glib/ListG.d` | >0 | ❌ `Signal 11 (core dumped)` |
| `generated/gtkd/glib/ListSG.d` | >0 | ❌ `Signal 11 (core dumped)` |
| `generated/gtkd/gobject/ObjectG.d` | >0 | ❌ `Signal 11 (core dumped)` |

全库 906 模块合跑时，崩溃前的输出透露了真相：

```
Library load failed (librsvg-2.so.2)
Library load failed (libharfbuzz-gobject.so.0)
Signal 11 (core dumped)
```

**误导性**：日志主体只有一行 `Signal 11`，容易被读成「该库在 OHOS 上有 bug / 平台不支持 / 需打补丁」。而真实原因是 **ohpcd 的 librsvg 是静态制品**（只有 `librsvg-2.a`，不提供 `librsvg-2.so.2`）—— 一个**运行环境缺共享库**的问题。

## Root Cause（崩溃机制）

启动序列早期，某个模块的构造器内 `dlopen` 失败 → `Loader.d:104` 抛异常 → 异常发生在**模块构造阶段**（`main` 之前/极早期），此时没有可用的浮现路径 → 在 OHOS/musl 上表现为**进程直接 SIGSEGV**，而不是可读的 `Error loading shared library ...` 错误。

两个层次要分开看：

1. **为什么崩**：启动期急切登记 + 缺件 → 构造阶段异常 → SIGSEGV。
2. **为什么难查**：错误信息在构造阶段被销毁，只剩 `Signal 11`；且「缺件」与「平台不支持」在该表象下**完全同形**。

## Recommended Solution

### 第一步：分类（**最关键，不可跳过**）

先把「环境缺件」与「库真崩溃」分开，用**不经该绑定**的手段取证：

```bash
# ① 目标 .so 的符号是否齐备且可加载（绕开 gtkd 的加载器）
python3 -c "
import ctypes
g = ctypes.CDLL('libgobject-2.0.so.0', mode=ctypes.RTLD_GLOBAL)
for s in ('g_value_init','g_value_get_int','g_value_set_int','g_object_new'):
    try: getattr(g, s); print(f'{s:20s} OK')
    except AttributeError: print(f'{s:20s} MISSING')
"
# → 全部 OK 即证明「符号齐备」，排除「平台缺能力」

# ② 隔离运行，找出「通过」与「崩溃」的分界
<逐模块/逐用例驱动>   # 通过的通常是纯计算、不触发加载器的那些
```

本案例的结论链：`glib/c/types.d`（`Linker.link` 调用数 0）通过 + gobject 符号经 ctypes 直查全部 OK → **证明是「环境缺共享库」而非「库本体崩溃」**。

### 第二步：补齐运行期依赖

把每个 dlopen 目标声明为配方依赖，并确认是**共享版**真的在 `LD_LIBRARY_PATH` 上：

```python
# 注意：静态制品不能替代（本条踩坑点）
self.requires("gtk/3.24.43")
self.requires("librsvg/2.62.3.1")   # 需共享版 .so；若 ohpcd 只有静态版 → 环境缺口
```

> ⚠️ **静态库制品无法用于运行期 dlopen**。若制品仓只发布静态版，这不是配方能修的，
> 应如实记录为环境缺口并说明影响面（本例：仅影响 `librsvg` 相关的加载路径）。

### 第三步：确实无法补齐时——探针判定 + 如实申报

禁止硬编码跳过。正确做法：

1. **探针实测**（如本仓 `_rtld_global_propagates()` 模式：现场编译两个互引 `.so`，子进程验证能力），只在确认不可用时才 deselect；
2. **如实申报** `N 通过 / M 崩溃`（R51），**不把 SIGSEGV 写成「通过」，也不写「不适用」**；
3. **给出反证**：符号可解析 + 加载器本身在同一包的另一路径可用；
4. **交付物可用性由消费者测试独立取证**（本例：11/11，同一 `Linker` 成功调用 `gtk_get_major_version()` 返回 3）。

### 回退方案（priority 2）：隔离 + 如实申报

补齐不可行时，逐模块隔离取真实通过/崩溃数，在 `manifest.yaml` / `notes.md` / `MANIFEST.yml` 三处如实记录崩溃机制与反证。禁止因 SIGSEGV 就笼统断言「该库在 OHOS 上不可用」。

## 反面模式（forbid）

| 模式 | 为什么禁止 | 后果 |
|---|---|---|
| 见到 `Signal 11` 就断言「平台不支持/库不兼容/需打补丁」 | SIGSEGV 只是**表象**，根因可能是「环境缺一个 .so」这种完全可修的问题 | 把可修问题升级成平台限制，并掩盖真实缺口（如制品仓只发静态版） |
| 给上游模块构造器的 `dlopen` 加 `try/catch` 当修法 | 只是把崩溃变成「静默少符号」，运行期调用到该符号时仍空指针崩溃（更晚、更难查）；且属改上游源码 | 崩溃点后移，诊断难度上升 |

## 验证记录

| 项 | 值 |
|---|---|
| 案例 | gtkd 3.11.0（D 语言 GTK+3 绑定，运行期 dlopen 型） |
| 环境 | HarmonyOS PC / OpenHarmony，aarch64-linux-ohos，LDC 1.42.0（LLVM 20.1.0） |
| 崩溃表现 | 4 个内嵌 unittest 块逐个隔离：**1 通过 / 3 SIGSEGV** |
| 根因取证 | ① 合跑输出打印 `Library load failed (librsvg-2.so.2)` / `(libharfbuzz-gobject.so.0)`；② 唯一通过者 `Linker.link` 调用数为 0（纯 D 计算）；③ ctypes 直查 `libgobject-2.0.so.0` 的 `g_value_init` 等符号**全部 OK** |
| 结论 | **「环境缺共享库」而非「库本体崩溃」**——ohpcd 的 librsvg 为静态制品，无 `librsvg-2.so.2` |
| 交付物反证 | 库本体完整编译出 5 个静态库；消费者测试 **11/11**（同一 `Linker` 经 dlopen 调 `gtk_get_major_version()` 返回 3） |

## 关联

- `E004` — musl BIND_NOW 致扩展符号无法解析（**可读**报错；与本条「不可读」形成对照）
- `E024` — AF_UNIX bind 被拒（同为平台限制，但错误可读）
- `opencsg-1.8.2-dt-needed-verification-for-runtime-dlopen-libs` — 运行期 dlopen 型库的产物验证
- `DRAFT-libcec-8.1.7-cmake-system-name-linux-soname` — dlopen 目标的 soname 命名/查找
- `DRAFT-test-discovery-per-language-convention` — 先按语言惯例找到测试，再面对其运行崩溃
